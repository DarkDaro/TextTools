"""
obsidian_check — валидатор метафайлов Obsidian (24.10).

Проверяет то, что Obsidian молча ломает при чтении:
  FM_UNCLOSED/FM_YAML  — frontmatter открыт без пары или невалидный YAML
  ENC_NOT_UTF8         — файл не читается как UTF-8 (номер строки по байту ошибки)
  FENCE_UNCLOSED       — незакрытый ```code fence
  BAD_SEP/TBL_COLS     — таблица без разделителя / число колонок не совпало
  TBL_PIPE_IN_CODE     — '|' внутри `кода` в ячейке рвёт таблицу (чинится --fix)
  H_NO_SPACE           — '#' без пробела (Obsidian не сделает заголовок)
  H_EMPTY/H_MULTI_H1/H_JUMP — пустые заголовки, несколько H1, пропуск уровня
  WIKI_BROKEN/WIKI_ATTACH_MISSING — [[ссылки]] и вложения не найдены
  MDLINK_BROKEN        — markdown-ссылка на несуществующий локальный файл
  TAG_NUMERIC          — числовой тег (#1), Obsidian его не создаёт
  EXPLODED             — посимвольно разбитый текст (потерянные переводы строк)

Severity: ERROR — Obsidian рендерит неверно или теряет данные.
          WARN  — рендерится, но структура/навигация сломаны.
          INFO  — косметика.

  python textools.py obsidian-check --input <vault> [--fix] [--exit-zero] [--out report.md]
      [--limit N] [--verbose]

--fix правит только машинно-однозначное: frontmatter-значения и
wikilinks-списки, '|' внутри `кода` в таблицах, посимвольные блоки.
Всё остальное — только отчёт.
Правки с бэкапом .bak (порядок: бэкап -> запись -> проверка).
Код возврата 1, если остались ERROR; --exit-zero всегда даёт 0.
"""
import argparse
import os
import re
# 26.10: shutil не используется (мёртвый импорт) — отключён
# import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.text_parser import backup_once, stop_requested

try:
    import yaml
except ImportError:  # frontmatter-проверка просто отключится
    yaml = None

SKIP_DIRS = {".obsidian", ".git", ".trash", ".smart-env", "md_replace_backups",
             "reports", "__pycache__"}

SEVERITY = {
    "FM_UNCLOSED": "ERROR",
    "FM_YAML": "ERROR",
    "FENCE_UNCLOSED": "ERROR",
    "BAD_SEP": "ERROR",
    "TBL_COLS": "ERROR",
    "TBL_PIPE_IN_CODE": "ERROR",
    "H_NO_SPACE": "ERROR",
    "EXPLODED": "ERROR",
    "ENC_NOT_UTF8": "ERROR",
    "READ_FAIL": "WARN",
    "FM_DESC": "WARN",
    "FM_TAGS": "WARN",
    "H_EMPTY": "WARN",
    "WIKI_BROKEN": "WARN",
    "WIKI_ATTACH_MISSING": "WARN",
    "MDLINK_BROKEN": "WARN",
    "H_MULTI_H1": "INFO",
    "H_JUMP": "INFO",
    "TAG_NUMERIC": "INFO",
    "WIKI_EMPTY": "INFO",
}

# 24.10: порядок severity для сортировки сводки и подробностей
SEVERITY_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}

FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
HEADING_RE = re.compile(r"^(#{1,6})(\s+|$)")
NOT_A_HEADING_RE = re.compile(r"^(#{1,6})[^\s#]")
SEP_RE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
WIKI_RE = re.compile(r"\[\[([^\[\]]*)\]\]")
MDLINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
TAG_RE = re.compile(r"(?<![\w`&#])#([^\s#\[\](){}<>.,;:!?'\"`]+)")
CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
RISKY_VALUE_RE = re.compile(r"^(\s*[\w.\-]+\s*:\s*)(.+)$")


def iter_md(root, limit=None):
    root = Path(root)
    if root.is_file():
        if not root.name.endswith(".bak"):
            yield root
        return
    count = 0
    for p in sorted(root.rglob("*.md")):
        # 24.10: служебные папки считаем относительно корня, иначе
        # явно указанная папка reports/ пропускалась бы целиком
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        if limit is not None and count >= limit:
            return
        count += 1
        yield p


def read_text(path):
    return path.read_bytes().decode("utf-8-sig")


def split_cells(row):
    body = row.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells, buf, esc = [], [], False
    for ch in body:
        if esc:
            buf.append(ch)
            esc = False
        elif ch == "\\":
            esc = True
            buf.append(ch)
        elif ch == "|":
            cells.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    cells.append("".join(buf))
    return cells


def escape_code_pipes(row):
    def repl(m):
        return m.group(0).replace("\\|", "|").replace("|", "\\|")

    return CODE_SPAN_RE.sub(repl, row)


def strip_code_lines(lines):
    out = []
    fence = None
    for i, line in enumerate(lines, 1):
        m = FENCE_RE.match(line)
        if m:
            token = m.group(1)[0] * 3
            if fence is None:
                fence = token
                out.append((i, line, True))
                continue
            if line.strip().startswith(fence):
                fence = None
                out.append((i, line, True))
                continue
        out.append((i, line, fence is not None))
    return out


def check_frontmatter(lines, add):
    if not lines or lines[0].strip() != "---":
        return
    end = None
    for i in range(1, min(len(lines), 200)):
        if lines[i].strip() in ("---", "..."):
            end = i
            break
    if end is None:
        add("FM_UNCLOSED", 1, "frontmatter открыт '---', пара не найдена")
        return
    if yaml is None:
        return
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as e:
        add("FM_YAML", 1, "невалидный YAML: " + str(e).replace("\n", " ")[:150])
        return
    if not isinstance(data, dict):
        add("FM_YAML", 1, "frontmatter не словарь (получилось %s)" % type(data).__name__)
        return
    desc = data.get("description")
    if desc is None:
        add("FM_DESC", 1, "нет поля description")
    elif not str(desc).strip():
        add("FM_DESC", 1, "пустой description")
    tags = data.get("tags")
    if tags is not None and not isinstance(tags, (list, str)):
        add("FM_TAGS", 1, "tags должен быть списком или строкой")


def check_headings(scanned, add):
    levels, h1 = [], 0
    for lineno, line, in_code in scanned:
        if in_code:
            continue
        if NOT_A_HEADING_RE.match(line):
            add("H_NO_SPACE", lineno, "нет пробела после '#': " + line.strip()[:60])
            continue
        m = HEADING_RE.match(line)
        if not m:
            continue
        lvl = len(m.group(1))
        if not line[lvl:].strip():
            add("H_EMPTY", lineno, "пустой заголовок из %d решёток" % lvl)
            continue
        if lvl == 1:
            h1 += 1
        if levels and lvl > levels[-1] + 1:
            add("H_JUMP", lineno, "уровень H%d после H%d" % (lvl, levels[-1]))
        levels.append(lvl)
    if h1 > 1:
        add("H_MULTI_H1", 0, "H1 встречается %d раз" % h1)


def check_tables(scanned, add):
    block = []
    for lineno, line, in_code in scanned + [(0, "", True)]:
        if (not in_code) and line.lstrip().startswith("|"):
            block.append((lineno, line))
            continue
        if len(block) >= 2:
            h_ln, header = block[0]
            s_ln, sep = block[1]
            if not SEP_RE.match(sep):
                add("BAD_SEP", s_ln, "вторая строка — не разделитель |---|")
            else:
                ncols = len(split_cells(header))
                if len(split_cells(sep)) != ncols:
                    add("TBL_COLS", s_ln, "разделитель на %d, шапка на %d" % (len(split_cells(sep)), ncols))
                for ln, row in block[2:]:
                    if SEP_RE.match(row):
                        continue
                    escaped = escape_code_pipes(row)
                    if escaped != row:
                        add("TBL_PIPE_IN_CODE", ln,
                            "вертикальная черта внутри `кода` рвёт ячейку (чинится --fix)")
                        row = escaped
                    have = len(split_cells(escape_code_pipes(row)))
                    if have != ncols:
                        add("TBL_COLS", ln, "строка на %d колонок, шапка на %d: %s"
                            % (have, ncols, row.strip()[:70]))
        block = []


def check_tags(scanned, add):
    for lineno, line, in_code in scanned:
        if in_code:
            continue
        for m in TAG_RE.finditer(re.sub(r"`[^`]*`", "", line)):
            if m.group(1).isdigit():
                add("TAG_NUMERIC", lineno, "числовой тег #%s — Obsidian его не создаёт" % m.group(1))


def find_exploded_runs(lines, min_run=40):
    """Ищет блоки «один символ на строку». Пустые строки сами по себе
    (обычные отбивки абзацев) блоком не считаются: в развалине должны
    преобладать одиночные непробельные символы."""
    runs, start, run = [], None, 0

    def _exploded(block):
        chars = [ln for ln in block if len(ln) == 1]
        if len(chars) < max(20, min_run // 2):
            return False
        nonspace = sum(1 for ln in chars if not ln.isspace())
        return nonspace >= len(chars) * 0.6

    for i, line in enumerate(lines):
        if len(line) <= 1:
            if start is None:
                start = i
            run += 1
            continue
        if run >= min_run and _exploded(lines[start:start + run]):
            runs.append((start, run))
        start, run = None, 0
    if run >= min_run and _exploded(lines[start:start + run]):
        runs.append((start, run))
    return runs


def check_links(path, scanned, index, add):
    # Obsidian не считает ссылкой то, что внутри `кода` и code fence.
    # Код маскируется пробелами той же длины: позиции и номера строк целы.
    for lineno, line, in_code in scanned:
        if in_code:
            continue
        masked = CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), line)
        for m in WIKI_RE.finditer(masked):
            raw = m.group(1)
            target = raw.split("|")[0].split("#")[0].strip()
            if raw.strip() in ("", "..."):
                add("WIKI_EMPTY", lineno, "пустая wikilink [[%s]]" % raw)
                continue
            if not target or target.startswith(("http://", "https://")):
                continue
            base = target.replace("\\", "/").rstrip("/")
            key = base.lower().removesuffix(".md")
            name = key.rsplit("/", 1)[-1]
            if "." in name:
                if ".." in name:
                    continue  # "batch1..4.txt" — диапазон в тексте, не файл
                if key not in index["attachments"] and name not in index["attachments"]:
                    add("WIKI_ATTACH_MISSING", lineno,
                        "[[%s]] — вложение не найдено" % raw)
                continue
            if key in index["relpaths"] or name in index["stems"]:
                continue
            add("WIKI_BROKEN", lineno, "[[%s]] — файл не найден" % raw)
        for m in MDLINK_RE.finditer(masked):
            target = m.group(1)
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if target[:1] in "+-~" or ".." in target:
                continue
            target = target.split("#")[0]
            if not target:
                continue
            if not (path.parent / target.replace("/", "\\")).exists():
                add("MDLINK_BROKEN", lineno, "](%s) — файл не найден" % m.group(1))


def build_index(files, vault_root):
    relpaths, stems, attachments = set(), set(), set()
    for p in files:
        try:
            rel = p.relative_to(vault_root).with_suffix("").as_posix().lower()
        except ValueError:
            rel = p.with_suffix("").as_posix().lower()
        relpaths.add(rel)
        stems.add(p.stem.lower())
    for p in vault_root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.relative_to(vault_root).parts):
            continue
        if not p.is_file():
            continue
        attachments.add(p.name.lower())
    # [[reference/...]] из логов ведут в память агента — добавляем её в индекс
    mem = os.environ.get("MEMORY_DIR")
    if mem and Path(mem).is_dir():
        for p in Path(mem).rglob("*.md"):
            try:
                relpaths.add(p.relative_to(mem).with_suffix("").as_posix().lower())
            except ValueError:
                pass
            stems.add(p.stem.lower())
    return {"relpaths": relpaths, "stems": stems, "attachments": attachments}


def validate_file(path, index):
    findings = []

    def add(code, lineno, msg):
        findings.append((path, lineno, code, msg))

    try:
        data = path.read_bytes()
    except OSError as e:
        findings.append((path, 0, "READ_FAIL", str(e)[:120]))
        return findings
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        line = data[:e.start].count(b"\n") + 1
        add("ENC_NOT_UTF8", line,
            "файл не в UTF-8 (ошибка на байте %d: %s)" % (e.start, e.reason))
        return findings
    lines = text.splitlines()
    check_frontmatter(lines, add)
    scanned = strip_code_lines(lines)
    open_fence = None
    for lineno, line, _c in scanned:
        if FENCE_RE.match(line):
            open_fence = None if open_fence else lineno
    if open_fence:
        add("FENCE_UNCLOSED", open_fence, "code fence не закрыт")
    for start, count in find_exploded_runs(lines):
        add("EXPLODED", start + 1, "посимвольно разбитый блок, %d строк" % count)
    check_headings(scanned, add)
    check_tables(scanned, add)
    check_tags(scanned, add)
    check_links(path, scanned, index, add)
    return findings


def needs_quote(value):
    v = value.strip()
    if not v or v[0] in "\"'|>":
        return False
    return bool(": " in v or v.endswith(":") or v[0] in "[{&*!%@`" or " #" in v)


WIKILINK_IN_VALUE_RE = re.compile(r"^\s*[\[{].*\[\[.*\]\].*[\]}]\s*$")


def split_wikilinks(value):
    """Вытаскивает отдельные [[ссылки]] из строки, отбрасывая текст-пояснения."""
    return re.findall(r"\[\[[^\[\]]+\]\]", value)


def is_wikilink_container(value):
    """Значение — строка или список из одних wikilinks (Obsidian-связи)."""
    v = value.strip()
    if v[:1] in "\"'" and v[-1:] == v[:1]:
        v = v[1:-1].strip()
    if v[:1] not in "[{\"'" and "[[" not in v:
        return False
    links = split_wikilinks(v)
    if not links:
        return False
    rest = v
    for link in links:
        rest = rest.replace(link, "")
    rest = rest.strip().strip("[]{}").strip()
    return rest.replace(",", "").replace(" ", "") == ""

def wikilinks_to_list(lines, index, key_indent, value):
    """YAML-список ссылок: связи в свойствах Obsidian иначе не работают."""
    links = split_wikilinks(value)
    key = lines[index].split(":", 1)[0]
    lines[index] = key + ":"
    pad = " " * (key_indent + 2)
    lines[index + 1:index + 1] = ['%s- "%s"' % (pad, l) for l in links]
    return len(links)


def fix_text(text):
    """Возвращает (new_text, счётчики). Правит только однозначное."""
    # смешанные переводы строк: режем универсально, пишем доминирующий
    nl = "\r\n" if text.count("\r\n") * 2 > text.count("\n") else "\n"
    trailing = text.endswith(nl)
    lines = text.splitlines()
    counters = Counter()

    # 1. frontmatter: wikilinks -> YAML-список, остальное проблемное -> в кавычки
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, min(len(lines), 200))
                    if lines[i].strip() in ("---", "...")), None)
        if end is not None:
            i = 1
            while i < end:
                m = RISKY_VALUE_RE.match(lines[i])
                if not m:
                    i += 1
                    continue
                value = m.group(2)
                if is_wikilink_container(value):
                    indent = len(lines[i]) - len(lines[i].lstrip())
                    added = wikilinks_to_list(lines, i, indent, value.strip().strip("\"'"))
                    end += added  # список вырос на added строк
                    counters["wikilinks"] += added
                    i += added + 1
                    continue
                if needs_quote(value):
                    v = value.strip()
                    lines[i] = m.group(1) + '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
                    counters["frontmatter"] += 1
                i += 1

    # 2. посимвольные блоки: '' -> перевод строки
    runs = find_exploded_runs(lines)
    if runs:
        out, pos = [], 0
        for start, count in runs:
            out.extend(lines[pos:start])
            blob = "".join("\n" if not ln else ln for ln in lines[start:start + count])
            out.extend(blob.split("\n"))
            pos = start + count
            counters["exploded"] += 1
        out.extend(lines[pos:])
        lines = out

    # 3. таблицы: '|' внутри `кода`
    fence, changed = None, 0
    i = 0
    while i < len(lines):
        m = FENCE_RE.match(lines[i])
        if m:
            fence = None if fence else m.group(1)[0] * 3
            i += 1
            continue
        if fence is None and lines[i].lstrip().startswith("|"):
            block = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                block.append(i)
                i += 1
            changed += _fix_table_block(lines, block)
            continue
        i += 1
    if changed:
        counters["table"] += changed
    new_text = nl.join(lines)
    if trailing:
        new_text += nl
    return new_text, counters


def _fix_table_block(lines, block):
    if len(block) < 2 or not SEP_RE.match(lines[block[1]]):
        return 0
    ncols = len(split_cells(lines[block[0]]))
    changed = 0
    for idx in block:
        if idx == block[1]:
            continue
        original = lines[idx]
        row = escape_code_pipes(original)
        if row == original:
            continue
        cells = split_cells(row)
        if len(cells) != ncols:
            continue  # лишние ячейки — решение человека
        lines[idx] = "| " + " | ".join(c.strip() for c in cells) + " |"
        changed += 1
    return changed


def run(input_path, limit=None, fix=False, verbose=False, out=None, no_bak=False,
        exit_zero=False):
    vault_root = Path(input_path)
    if vault_root.is_file():
        vault_root = vault_root.parent
    files = list(iter_md(input_path, limit))
    index = build_index(files, vault_root)

    total = len(files)
    if total:
        print(f"PROGRESS:0/{total}", flush=True)

    report = []
    applied = []          # (файл, что исправлено) — для отчёта «сделано»
    counters = Counter()
    done = 0
    stopped = False
    for idx, p in enumerate(files, 1):
        # 24.10: мягкая остановка из GUI (stop.flag) — между файлами
        if stop_requested():
            stopped = True
            print("Остановлено пользователем.", flush=True)
            break
        if fix:
            try:
                raw = p.read_bytes().decode("utf-8-sig")
            except (OSError, UnicodeDecodeError):
                raw = None
            if raw is not None:
                new_text, c = fix_text(raw)
                if c and new_text != raw:
                    if not no_bak:
                        # 24.10: как во всей утилите — существующий .bak
                        # не затирается, он хранит оригинал до первой правки
                        backup_once(p)
                    p.write_text(new_text, encoding="utf-8", newline="")
                    counters.update(c)
                    applied.append((p, dict(c)))
        report.extend(validate_file(p, index))
        done += 1
        print(f"PROGRESS:{idx}/{total}", flush=True)

    by_code = Counter(r[2] for r in report)
    by_sev = Counter(SEVERITY.get(r[2], "WARN") for r in report)
    lines = []
    if stopped:
        lines.append("Прогон прерван: обработано %d из %d файлов" % (done, total))
        lines.append("")
    if fix:
        lines.append("Исправлено автоматом: файлов %d (frontmatter %d, wikilinks-списки %d, таблицы %d, блоки-развалины %d)"
                     % (len(applied), counters["frontmatter"], counters["wikilinks"],
                        counters["table"], counters["exploded"]))
        lines.append("")
    lines.append("Файлов: %d, замечаний: %d" % (done, len(report)))
    lines.append("ERROR %d | WARN %d | INFO %d" % (by_sev["ERROR"], by_sev["WARN"], by_sev["INFO"]))
    lines.append("")
    for code, n in sorted(by_code.items(),
                          key=lambda kv: (SEVERITY_ORDER.get(SEVERITY.get(kv[0], "WARN"), 1),
                                          -kv[1])):
        lines.append("%-7s %-18s %d" % (SEVERITY.get(code, "WARN"), code, n))
    if applied:
        lines.append("")
        lines.append("Что исправлено:")
        for p, c in applied:
            parts = []
            if c.get("frontmatter"):
                parts.append("frontmatter %d" % c["frontmatter"])
            if c.get("wikilinks"):
                parts.append("wikilinks->список %d" % c["wikilinks"])
            if c.get("table"):
                parts.append("таблицы %d" % c["table"])
            if c.get("exploded"):
                parts.append("развалина %d" % c["exploded"])
            lines.append("  %s — %s" % (p.name, ", ".join(parts)))
    lines.append("")
    for path, lineno, code, msg in sorted(
            report, key=lambda r: (SEVERITY_ORDER.get(SEVERITY.get(r[2], "WARN"), 1),
                                   r[2], str(r[0]), r[1])):
        rel = path.relative_to(vault_root) if vault_root in path.parents else path
        loc = "%s:%d" % (rel.as_posix() if isinstance(rel, Path) else rel, lineno) if lineno else str(rel)
        lines.append("%-7s %-18s %s | %s" % (SEVERITY.get(code, "WARN"), code, loc, msg))

    # первая строка с кодом — там начинается сводка по кодам.
    # 24.10: на чистом vault кодов нет — next() без значения падал
    codes_start = next((k for k, l in enumerate(lines)
                        if l.startswith(("ERROR   ", "WARN    ", "INFO    "))),
                       len(lines))
    print("\n".join(lines[:codes_start]))
    print("\n".join(lines[codes_start:codes_start + len(by_code)]))
    if verbose:
        print("\n".join(lines[codes_start + len(by_code):]))
    if out:
        out_path = Path(out)
        if out_path.parent and not out_path.parent.exists():
            out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(lines), encoding="utf-8")
        print("\nОтчёт: %s" % out)
    # 24.10: если остались ERROR — код 1, чтобы проверку можно было
    # ставить в скрипты и pre-commit. --exit-zero нужен GUI и конвейерам,
    # где находки не должны выглядеть как сбой запуска.
    if not exit_zero and by_sev["ERROR"]:
        return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="obsidian-check", description="Валидатор метафайлов Obsidian")
    ap.add_argument("--input", required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--fix", action="store_true", help="править однозначное (с .bak)")
    ap.add_argument("--no-bak", action="store_true",
                    help="не делать .bak (для папок под git)")
    ap.add_argument("--exit-zero", action="store_true",
                    help="всегда код 0, даже если найдены ERROR (для GUI)")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    return run(args.input, args.limit, args.fix, args.verbose, args.out,
               args.no_bak, args.exit_zero)


if __name__ == "__main__":
    sys.exit(main())
