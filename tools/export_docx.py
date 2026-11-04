# -*- coding: utf-8 -*-
"""
export_docx — экспорт главы .md → .docx (05.11, BACKLOG №4).

Бета-ридеры и редакторы живут в Word; сейчас путь «md → docx» ручной.
Обратная задача (чтение docx) уже решена в core.docx_io.

Что понимает (осторожный минимум, без «улучшений» текста):
  - frontmatter (--- ... ---) — пропускается;
  - заголовки #..###### → стили Word Heading 1..6;
  - абзацы; диалоговые строки с тире — обычные абзацы;
  - списки «- » и «* » → стиль List Bullet; нумерованные «1. » —
    обычные абзацы с текстом номера (стиль List Number в python-docx
    продолжает нумерацию по всему документу — это ломает список);
  - цитаты «> » → стиль Quote;
  - код-блоки ``` → моноширинные абзацы (Courier New);
  - горизонтальная черта --- / *** → центральная «* * *»;
  - таблицы md → строки текста с « | » (Word-таблицы не строим);
  - инлайн: **жирный**, *курсив*, `код`, [[вики-ссылка|алиас]] (в
    текст идёт алиас или цель), [текст](url) → «текст (url)».

Чего НЕ делает (сознательно): не правит ё/е и типографику — текст
уходит в Word как написан; правки делаются ДО экспорта (yo,
typography), иначе бэкапы и отчёты перестают соответствовать файлу.

Использование:
  python textools.py export-docx --input глава.md --out глава.docx
  python textools.py export-docx --input папка --out папка_docx [--force]

Файл → файл; папка → папка: каждый .md → одноимённый .docx, вложенные
папки воспроизводятся. Существующие .docx перезаписываются только
с --force (экспорт молча затирать нельзя).
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MD_EXTS = (".md", ".markdown")
HR_RE = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
BULLET_RE = re.compile(r"^[-*]\s+(.+)$")
NUMBERED_RE = re.compile(r"^\d+[.)]\s+(.*)$")
QUOTE_RE = re.compile(r"^>\s?(.*)$")
# инлайн-разметка: жирный, курсив, код, вики-ссылка, md-ссылка
INLINE_RE = re.compile(
    r"\*\*(?P<bold>.+?)\*\*"
    r"|\*(?P<ital>[^*\n]+?)\*"
    r"|`(?P<code>[^`\n]+?)`"
    r"|\[\[(?P<wikilink>[^\]|]+?)(?:\|(?P<alias>[^\]]+?))?\]\]"
    r"|\[(?P<linktext>[^\]]+?)\]\((?P<url>[^)\s]+?)\)"
)


def add_inline(par, text):
    """Инлайн-разметка строки → runs абзаца (жирный/курсив/код/ссылки)."""
    pos = 0
    for m in INLINE_RE.finditer(text):
        if m.start() > pos:
            par.add_run(text[pos:m.start()])
        if m.group("bold") is not None:
            r = par.add_run(m.group("bold"))
            r.bold = True
        elif m.group("ital") is not None:
            r = par.add_run(m.group("ital"))
            r.italic = True
        elif m.group("code") is not None:
            r = par.add_run(m.group("code"))
            r.font.name = "Courier New"
        elif m.group("wikilink") is not None:
            par.add_run((m.group("alias") or m.group("wikilink")).strip())
        elif m.group("linktext") is not None:
            par.add_run(f"{m.group('linktext')} ({m.group('url')})")
        pos = m.end()
    if pos < len(text):
        par.add_run(text[pos:])


def _add_par(doc, text="", style=None, mono=False, center=False):
    try:
        par = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    except KeyError:
        # стиль отсутствует в шаблоне — обычный абзац
        par = doc.add_paragraph()
    if center:
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if text:
        add_inline(par, text)
    if mono:
        for r in par.runs:
            r.font.name = "Courier New"
            from docx.shared import Pt
            r.font.size = Pt(9)
    return par


def _is_table_separator(row):
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c) for c in cells)


def _table_rows_to_text(row_lines):
    """Таблица md → строки «ячейка | ячейка»; разделитель |---| пропадает."""
    out = []
    for ln in row_lines:
        if _is_table_separator(ln):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        out.append(" | ".join(cells))
    return out


def convert_text(text, doc):
    """Заметка md → документ docx (in-place в переданный Document)."""
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.splitlines()

    # frontmatter пропускается целиком
    start = 0
    if lines and lines[0].strip() == "---":
        start = 1
        while start < len(lines) and lines[start].strip() != "---":
            start += 1
        start += 1

    i = start
    in_code = False
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("```"):
            in_code = not in_code
            i += 1
            continue
        if in_code:
            _add_par(doc, ln, mono=True)
            i += 1
            continue
        if not ln.strip():
            i += 1
            continue
        if HR_RE.match(ln.strip()):
            _add_par(doc, "* * *", center=True)
            i += 1
            continue
        m = HEADING_RE.match(ln)
        if m:
            level = len(m.group(1))
            try:
                head = doc.add_heading("", level=level)
            except KeyError:
                head = _add_par(doc)
            add_inline(head, m.group(2))
            i += 1
            continue
        if ln.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(lines[i])
                i += 1
            for row in _table_rows_to_text(rows):
                _add_par(doc, row)
            continue
        m = QUOTE_RE.match(ln)
        if m:
            _add_par(doc, m.group(1), style="Quote")
            i += 1
            continue
        m = BULLET_RE.match(ln)
        if m:
            _add_par(doc, m.group(1), style="List Bullet")
            i += 1
            continue
        m = NUMBERED_RE.match(ln)
        if m:
            # нумерация — текстом: стиль List Number продолжает счёт
            # по всему документу и ломает второй список
            _add_par(doc, ln.strip())
            i += 1
            continue
        _add_par(doc, ln)
        i += 1


def convert_file(src, dst):
    """Один .md → .docx. Возвращает число абзацев."""
    from docx import Document
    doc = Document()
    props = doc.core_properties
    props.author = "TextTools"
    props.title = Path(src).stem
    text = Path(src).read_text(encoding="utf-8", errors="replace")
    convert_text(text, doc)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(dst))
    return len(doc.paragraphs)


def run(input_path, out, force=False, limit=None):
    from core.text_parser import check_root
    root = check_root(input_path)
    if root.is_file():
        if root.suffix.lower() not in MD_EXTS:
            print(f"Ошибка: {root.name} — не .md (нужен markdown-файл)")
            return 2
        out_p = Path(out) if str(out).strip() else None
        if out_p is None or str(out).strip() == "-":
            print("Ошибка: --out обязателен (путь .docx)")
            return 2
        if out_p.suffix.lower() != ".docx":
            # файл → папка: кладём одноимённый .docx внутрь
            if out_p.exists() and out_p.is_dir():
                out_p = out_p / (root.stem + ".docx")
            else:
                out_p = out_p.with_suffix(".docx")
        if out_p.exists() and not force:
            print(f"Ошибка: {out_p} уже существует — перезапись только "
                  "с --force")
            return 2
        n = convert_file(root, out_p)
        print(f"Экспортировано: {out_p} (абзацев: {n})")
        return 0

    # папка → папка
    out_dir = Path(out) if str(out).strip() else None
    if not out_dir or str(out).strip() == "-":
        print("Ошибка: --out обязателен (папка для .docx)")
        return 2
    files = [f for f in sorted(root.rglob("*"))
             if f.is_file() and f.suffix.lower() in MD_EXTS
             and not f.name.endswith(".bak")]
    from core.text_parser import SKIP_PARTS
    files = [f for f in files if not (set(f.parts) & SKIP_PARTS)]
    if limit is not None and limit > 0:
        files = files[:limit]
    total = len(files)
    if not total:
        print(f"В {root} нет .md файлов — экспортировать нечего.")
        return 1
    print(f"PROGRESS:0/{total}", flush=True)
    made = 0
    for i, f in enumerate(files, 1):
        rel = f.relative_to(root).with_suffix(".docx")
        dst = out_dir / rel
        if dst.exists() and not force:
            print(f"  [ПРОПУЩЕН] {dst.name}: уже существует (--force — "
                  "перезаписать)")
            continue
        convert_file(f, dst)
        made += 1
        print(f"PROGRESS:{i}/{total}", flush=True)
    print(f"Готово: {made} файл(ов) в {out_dir}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="export-docx",
        description="Экспорт заметки/папки Obsidian (.md) в Word (.docx)")
    ap.add_argument("--input", required=True, help=".md файл или папка")
    ap.add_argument("--out", required=True,
                    help=".docx файл (для файла) или папка (для папки)")
    ap.add_argument("--force", action="store_true",
                    help="перезаписывать существующие .docx")
    ap.add_argument("--limit", type=int, help="максимум файлов (для папки)")
    args = ap.parse_args(argv)
    try:
        return run(args.input, args.out, force=args.force, limit=args.limit)
    except ValueError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
