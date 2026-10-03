# -*- coding: utf-8 -*-
"""
typography — приведение типографики к русской норме в .md/.txt/.docx.

  python typography.py --input <папка или файл> [--fix] [--nbsp]
      [--out report.md]

Правила (вне блоков кода ```, frontmatter .md и inline-кода `...`):
  1. «...» (3+ точки)  -> «…»
  2. «слово - слово» и «слово -- слово» -> «слово — слово»;
     недостающий пробел после тире: «слово —слово» -> «слово — слово»
     (диапазоны «2010—2015» не трогаются).
  3. Кавычки: „лапки“ и прямые "..." -> «ёлочки» — только парные в
     пределах строки и только вокруг текста с кириллицей (латиница, URL,
     строки с «=» не трогаются). Вложенная цитата: если «ёлочки» в строке
     уже есть, прямые кавычки становятся внутренними „лапками“.
  4. Диалоговое тире в начале строки «- Реплика» -> «— Реплика»
     (только .txt и .docx; в .md начало строки с «- » — это список).
  5. С --nbsp: неразрывный пробел после предлогов/союзов (в, и, с, на...),
     после «№» и перед тире (тире примыкает к предыдущему слову).

docx: правится только текст w:t; кавычки — в пределах одного w:t
(разорванные форматированием кавычки не трогаются — это безопаснее).

По умолчанию dry-run (ничего не меняет). С --fix — правит файлы,
создавая <имя>.bak рядом.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import text_parser as tp

SKIP_DIRS = {".git", ".obsidian", ".trash", "reports", "__pycache__"}
EXTS = (".md", ".txt", ".docx")
FENCE_RE = ("```", "~~~")

RE_DOTS = re.compile(r"\.{3,}")
RE_DASH_SP = re.compile(r"(?<=\S) - (?=\S)")            # слово - слово
RE_DASH_DB = re.compile(r"(?<=\S)(?: -- |--)(?=\S)")    # слово -- слово
# недостающий пробел после тире: «—слово» / «слово —слово»
RE_DASH_GAP = re.compile(r"(?<=\s)—(?=\S)")
RE_DIALOG = re.compile(r"^(\s*)- (?=\S)")               # «- Реплика» (txt/docx)
# «лапки» — внешние кавычки по русской норме это «ёлочки»
RE_LAPKI = re.compile(r"„([^“\"]*)“")
RE_URL = re.compile(r"https?://|www\.|\]\(")            # ссылки не трогаем
RE_CYR = re.compile(r"[А-Яа-яЁё]")
# короткие предлоги/союзы, после которых ставится неразрывный пробел
NBSP_WORDS = ("в", "и", "с", "к", "о", "у", "а", "но", "не", "ни", "на",
              "по", "за", "из", "от", "до", "об", "для", "при", "над",
              "под", "как", "что", "же", "ли", "бы", "б")
RE_NBSP = re.compile(
    r"(?<![\wА-Яа-яЁё-])(" + "|".join(NBSP_WORDS) + r") (?=\S)",
    re.IGNORECASE)
RE_NBSP_NUM = re.compile(r"(№) (?=\S)")
# тире не отрывается от предыдущего слова: пробел перед « — » неразрывный
RE_NBSP_DASH = re.compile(r"(?<=\S) (?=—(?:\s|$))")

RULE_KEYS = ("dots", "dash", "quotes", "nbsp")
RULE_TITLES = {"dots": "многоточия", "dash": "тире", "quotes": "«ёлочки»",
               "nbsp": "неразрывные пробелы"}


def _quotes(seg):
    """Кавычки -> «ёлочки». Возвращает (новый_фрагмент, пар).

    «лапки» „...“ заменяются на «ёлочки»; прямые кавычки "..." — тоже,
    но если во фрагменте уже есть «ёлочки» (вложенная цитата), прямые
    становятся внутренними „лапками“ — по правилам русской типографики."""
    # 1) „лапки“ -> «ёлочки» (простая обёртка, содержимое не трогаем)
    seg, k = RE_LAPKI.subn(r"«\1»", seg)
    n = k
    n_q = seg.count('"')
    if n_q == 0 or n_q % 2:
        return seg, n
    # защита: строки с «=» (yaml/html-атрибуты), ссылки, пустые пары
    if "=" in seg or RE_URL.search(seg):
        return seg, n
    parts = seg.split('"')
    contents = parts[1::2]
    if any(not c or not RE_CYR.search(c) for c in contents):
        return seg, n
    # вложенная цитата: «ёлочки» уже есть — прямые кавычки станут „лапками“
    outer = "«" in seg
    op, cl = ("„", "“") if outer else ("«", "»")
    out = [parts[0]]
    for i, c in enumerate(contents):
        out.append(op if i % 2 == 0 else cl)
        out.append(c)
        out.append(cl if i % 2 == 0 else op)
    return "".join(out) + parts[-1], n + len(contents)


def _nbsp(seg):
    """Неразрывные пробелы: после предлогов/союзов, после «№» и перед тире."""
    n = 0
    seg, k = RE_NBSP.subn(lambda m: m.group(1) + "\u00A0", seg)
    n += k
    seg, k = RE_NBSP_NUM.subn(lambda m: m.group(1) + "\u00A0", seg)
    n += k
    seg, k = RE_NBSP_DASH.subn("\u00A0", seg)
    n += k
    return seg, n


def _apply_inline(seg, nbsp, dialogue, counts):
    """Правила для одного фрагмента вне inline-кода."""
    seg, k = RE_DOTS.subn("…", seg)
    counts["dots"] += k
    seg, k = RE_DASH_SP.subn(" — ", seg)
    counts["dash"] += k
    seg, k = RE_DASH_DB.subn(" — ", seg)
    counts["dash"] += k
    seg, k = RE_DASH_GAP.subn("— ", seg)
    counts["dash"] += k
    if dialogue:
        seg, k = RE_DIALOG.subn(r"\1— ", seg)
        counts["dash"] += k
    seg, k = _quotes(seg)
    counts["quotes"] += k
    if nbsp:
        seg, k = _nbsp(seg)
        counts["nbsp"] += k
    return seg


def transform_text(text, nbsp=False, dialogue=False, frontmatter=False):
    """(новый_текст, счётчики по правилам). Блоки кода не трогаются.

    dialogue=True — конвертировать «- Реплика» в начале строки;
    frontmatter=True — пропустить yaml-блок "---...---" в начале файла."""
    counts = {k: 0 for k in RULE_KEYS}
    if not text:
        return text, counts
    lines = text.split("\n")
    out = []
    in_fence = False
    fence_marker = None
    in_fm = False
    for i, line in enumerate(lines):
        if frontmatter and i == 0 and line.strip() == "---":
            in_fm = True
            out.append(line)
            continue
        if in_fm:
            if line.strip() == "---":
                in_fm = False
            out.append(line)
            continue
        stripped = line.lstrip()
        if stripped.startswith(FENCE_RE):
            if not in_fence:
                in_fence, fence_marker = True, stripped[:3]
            elif stripped.startswith(fence_marker):
                in_fence, fence_marker = False, None
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        # inline-код `...`: правим только сегменты вне кода; при непарных
        # бэктиках сегментацию нельзя определить — кавычки/nbsp пропускаем
        if line.count("`") % 2 == 0:
            segs = line.split("`")
            for j in range(0, len(segs), 2):
                segs[j] = _apply_inline(segs[j], nbsp, dialogue, counts)
            line = "`".join(segs)
        else:
            line = _apply_inline(line, False, dialogue, counts)
        out.append(line)
    return "\n".join(out), counts


def collect(root):
    root = Path(root)
    if root.is_file():
        return [root] if root.suffix.lower() in EXTS else []
    files = []
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in EXTS:
            continue
        if set(f.parts) & SKIP_DIRS or f.name.endswith(".bak"):
            continue
        files.append(f)
    return files


def _fmt_counts(counts):
    return ", ".join(f"{RULE_TITLES[k]} {counts[k]}"
                     for k in RULE_KEYS if counts[k]) or "нет правок"


def run(input_path, fix=False, nbsp=False, out=None):
    files = collect(input_path)
    if not files:
        print("Файлы .md/.txt/.docx не найдены.")
        return 1
    total_files = 0
    totals = {k: 0 for k in RULE_KEYS}
    rows = []
    total = len(files)
    print(f"PROGRESS:0/{total}", flush=True)
    for idx, f in enumerate(files, 1):
        if tp.stop_requested():
            print("Остановлено пользователем.")
            break
        try:
            counts = None
            if f.suffix.lower() == ".docx":
                counts = fix_docx(f, nbsp, fix)
            else:
                text = f.read_text(encoding="utf-8")
                new_text, counts = transform_text(
                    text, nbsp=nbsp,
                    dialogue=f.suffix.lower() != ".md", frontmatter=True)
                if sum(counts.values()) and fix:
                    shutil.copy2(f, str(f) + ".bak")
                    f.write_text(new_text, encoding="utf-8")
        except (UnicodeDecodeError, PermissionError, OSError) as e:
            print(f"ПРОПУСК {f.name}: {e}")
            print(f"PROGRESS:{idx}/{total}", flush=True)
            continue
        print(f"PROGRESS:{idx}/{total}", flush=True)
        if sum(counts.values()):
            total_files += 1
            for k in RULE_KEYS:
                totals[k] += counts[k]
            rows.append((str(f), counts))
            print(f"{'[FIX] ' if fix else ''}{f}: {_fmt_counts(counts)}")
    grand = sum(totals.values())
    print(f"\nИтого: файлов с правками {total_files}, правок {grand} "
          f"({_fmt_counts(totals)})")
    if not fix and grand:
        print("Режим dry-run — файлы НЕ изменены. Для правки: --fix")
    if not nbsp:
        print("Неразрывные пробелы выключены (--nbsp)")
    if out:
        lines = [f"# Типографика — {input_path}",
                 f"Режим: {'ПРИМЕНЕНО (--fix)' if fix else 'dry-run (файлы не изменены)'}",
                 "",
                 "| Файл | многоточия | тире | «ёлочки» | неразрывные | Всего |",
                 "|---|---:|---:|---:|---:|---:|"]
        for path, c in rows:
            lines.append("| {} | {} | {} | {} | {} | {} |".format(
                path, c["dots"], c["dash"], c["quotes"], c["nbsp"],
                sum(c.values())))
        lines += ["",
                  f"**Итого:** файлов с правками {total_files}, правок {grand}.",
                  f"Неразрывные пробелы: {'включены' if nbsp else 'выключены (--nbsp)'}."]
        Path(out).write_text("\n".join(lines), encoding="utf-8")
    return 0


# --- docx ---

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DOC_PART_KEYWORDS = (
    "document.xml", "header", "footer", "footnotes", "endnotes", "comments")


def fix_docx(path, nbsp, fix):
    """Типографика docx: только текст w:t (тело, сноски, колонтитулы).
    Форматирование сохраняется. Кавычки конвертируются в пределах одного
    w:t — разорванные форматированием кавычки не трогаются (безопаснее)."""
    from docx import Document

    doc = Document(path)
    counts = {k: 0 for k in RULE_KEYS}
    for part in doc.part.package.iter_parts():
        name = str(part.partname)
        if "/word/" not in name or not any(k in name for k in DOC_PART_KEYWORDS):
            continue
        el = getattr(part, "_element", None)
        if el is None:
            continue
        for t_el in el.iter(W_NS + "t"):
            txt = t_el.text
            if not txt:
                continue
            new, c = transform_text(txt, nbsp=nbsp, dialogue=True)
            if sum(c.values()):
                t_el.text = new
                if new != new.strip():
                    t_el.set(
                        "{http://www.w3.org/XML/1998/namespace}space",
                        "preserve")
                for k in RULE_KEYS:
                    counts[k] += c[k]
    if sum(counts.values()) and fix:
        shutil.copy2(path, str(path) + ".bak")
        doc.save(path)
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser(description="Приведение типографики к русской норме")
    ap.add_argument("--input", required=True, help="папка или файл .md/.txt/.docx")
    ap.add_argument("--fix", action="store_true", help="реально править (с .bak)")
    ap.add_argument("--nbsp", action="store_true",
                    help="неразрывные пробелы после предлогов и «№»")
    ap.add_argument("--out", help="файл отчёта")
    args = ap.parse_args(argv)
    return run(args.input, fix=args.fix, nbsp=args.nbsp, out=args.out)


if __name__ == "__main__":
    sys.exit(main())
