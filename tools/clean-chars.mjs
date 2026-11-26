#!/usr/bin/env node
// Чистка иероглифов и мусорных символов в текстах и комментариях.
// Сканер идёт по всему содержимому файлов: и данные, и комментарии,
// и разметка. Легитимные символы проекта (статусы бэклога, скобки
// плейсхолдеров) в whitelist и не считаются мусором.
//
// Запуск из корня репозитория:
//   node tools/clean-chars.mjs            отчёт, выход 1 если есть мусор
//   node tools/clean-chars.mjs --fix      почистить файлы на месте
//   node tools/clean-chars.mjs --emoji    считать эмодзи мусором тоже
//   node tools/clean-chars.mjs <путь>     проверить файл или папку
//   npm run clean                         то же через package.json

import { readFileSync, writeFileSync, readdirSync, statSync } from "node:fs";
import { join, extname, relative, sep } from "node:path";

const args = process.argv.slice(2);
const fix = args.includes("--fix");
const emojiMode = args.includes("--emoji");
const rootArg = args.find((a) => !a.startsWith("--")) || ".";

// Символы, которые в этом репозитории легитимны: статусы задач
// (BACKLOG, TECH-DEBT) и скобки плейсхолдеров в примерах rules/.
const WHITELIST = new Set(["☐", "▶", "✅", "【", "】"]);

// Категории мусора: иероглифы, полная ширина, невидимые и управляющие.
const CATEGORIES = [
  ["иероглиф (CJK)", /[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]/],
  ["канa (хирагана/катакана)", /[\u3040-\u30FF]/],
  ["хангыль", /[\u1100-\u11FF\uAC00-\uD7AF]/],
  ["CJK-символы", /[\u3000-\u303F]/],
  ["полная ширина", /[\uFF00-\uFFEF]/],
  ["нулевая ширина/BOM", /[\u200B-\u200F\u2060-\u2064\uFEFF]/],
  ["управляющий символ", /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/],
  ["C1-управляющий", /[\u0080-\u009F]/],
  ["replacement-символ", /[\uFFFD]/],
  ["private use area", /[\uE000-\uF8FF]/],
  ["неразрывный пробел/soft hyphen", /[\u00A0\u00AD]/],
];

// Эмодзи и селекторы: отдельный режим, у проекта их быть не должно,
// кроме статусных маркеров из whitelist.
const EMOJI_RE = /[\u{1F000}-\u{1FAFF}\u{1F1E6}-\u{1F1FF}\u2600-\u27BF\u2B00-\u2BFF\uFE00-\uFE0F]/u;

const EXTENSIONS = new Set([
  ".html", ".js", ".mjs", ".cjs", ".css", ".md", ".json",
  ".txt", ".xml", ".svg", ".yml", ".yaml",
]);

const SKIP_DIRS = new Set([
  ".git", "node_modules", "out", ".github",
  "assets/art", "assets/audio", "assets/fonts", "archive",
]);

// Полная ширина FF01-FF5E переводится в ASCII сдвигом, пробельные
// варианты заменяются на обычный пробел, остальное удаляется.
function replaceChar(code) {
  if (code === 0x00a0 || code === 0x3000) return " ";
  if (code >= 0xff01 && code <= 0xff5e) return String.fromCharCode(code - 0xfee0);
  return "";
}

function categoryOf(code) {
  const ch = String.fromCodePoint(code);
  if (WHITELIST.has(ch)) return null;
  for (const [name, re] of CATEGORIES) {
    if (re.test(ch)) return name;
  }
  if (emojiMode && EMOJI_RE.test(ch)) return "эмодзи/селектор";
  return null;
}

function scanText(text) {
  const hits = [];
  const lines = text.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    for (let j = 0; j < line.length; j++) {
      const code = line.codePointAt(j);
      if (code > 0xffff) j++;
      const cat = categoryOf(code);
      if (cat) {
        const around = line.slice(Math.max(0, j - 24), j + 25).trim();
        hits.push({ line: i + 1, col: j + 1, code, cat, around });
      }
    }
  }
  return hits;
}

function cleanText(text) {
  let out = "";
  for (const ch of text) {
    const code = ch.codePointAt(0);
    out += categoryOf(code) === null ? ch : replaceChar(code);
  }
  return out;
}

function walk(dir) {
  const files = [];
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    const rel = relative(".", full);
    if (statSync(full).isDirectory()) {
      if (SKIP_DIRS.has(rel.split(sep).join("/")) || name.startsWith(".")) continue;
      files.push(...walk(full));
    } else if (!name.startsWith(".") && EXTENSIONS.has(extname(name))) {
      files.push(full);
    }
  }
  return files;
}

const targets = statSync(rootArg).isDirectory()
  ? walk(rootArg)
  : [rootArg];

let filesWithHits = 0;
let totalHits = 0;
let filesFixed = 0;

for (const file of targets) {
  const text = readFileSync(file, "utf8");
  const hits = scanText(text);
  if (!hits.length) continue;
  filesWithHits++;
  totalHits += hits.length;
  console.log(`\n${file}: находок ${hits.length}`);
  for (const h of hits.slice(0, 10)) {
    console.log(
      `  строка ${h.line}, символ ${h.col}: U+${h.code.toString(16).toUpperCase().padStart(4, "0")} ${h.cat} | …${h.around}…`
    );
  }
  if (hits.length > 10) console.log(`  … ещё ${hits.length - 10}`);
  if (fix) {
    const cleaned = cleanText(text);
    if (cleaned !== text) {
      writeFileSync(file, cleaned, "utf8");
      filesFixed++;
      console.log(`  почищен`);
    }
  }
}

console.log(
  `\nИтог: файлов проверено ${targets.length}, с находками ${filesWithHits}, мусора ${totalHits}` +
    (fix ? `, файлов почищено ${filesFixed}` : "")
);

if (!fix && totalHits > 0) {
  console.log("Запустите с --fix, чтобы почистить.");
  process.exit(1);
}
if (fix && filesFixed > 0) {
  console.log("Проверьте diff и прогоните гейты перед коммитом.");
}
