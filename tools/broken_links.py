"""
broken_links — вики- и markdown-ссылки на несуществующие файлы.

  python textools.py broken-links --input <vault> [--out report.md]
      [--limit N] [--verbose]

Проверяются оба синтаксиса Obsidian: [[вики-ссылки]] и markdown
[текст](цель). У markdown внешние адреса (http, mailto и т.п.) и чистые
якоря не считаются ссылками на файлы; изображения ![]() проверяются по
вложениям; относительные пути (./ ../) сверяются с диском относительно
папки заметки.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.report import write_report, write_json
from core import vault_scanner as vs


def _md_resolved(target, note, basenames, relpaths, attachments):
    """Цель markdown-ссылки существует? Индекс — как у вики-ссылок,
    плюс проверка по диску для относительных путей (./ ../)."""
    if vs.is_resolved(target, basenames, relpaths, attachments):
        return True
    try:
        return (note.path.parent / target).exists()
    except OSError:
        return False


def run(input_path, limit=None, verbose=False, out=None, json_out=None):
    notes, basenames, relpaths, attachments = vs.scan_vault(
        input_path, limit=limit)

    broken = []  # (note, target) — вики
    for n in notes:
        for t in sorted(n.links):
            if not vs.is_resolved(t, basenames, relpaths, attachments):
                broken.append((n, t))

    # 04.11: markdown-ссылки [текст](цель) — полная картина битых ссылок
    broken_md = []  # (note, исходная_цель)
    for n in notes:
        for _clean, raw in sorted(n.md_links):
            if not _md_resolved(_clean, n, basenames, relpaths, attachments):
                broken_md.append((n, raw))

    files_with_broken = sorted({n.rel for n, _ in broken})
    files_with_broken_md = sorted({n.rel for n, _ in broken_md})
    print(f"Заметок: {len(notes)}")
    print(f"Битых вики-ссылок: {len(broken)} "
          f"в {len(files_with_broken)} файлах")
    print(f"Битых markdown-ссылок: {len(broken_md)} "
          f"в {len(files_with_broken_md)} файлах")

    if verbose and broken:
        for n, t in broken[:40]:
            print(f"  {n.rel} -> [[{t}]]")
        if len(broken) > 40:
            print(f"  ... ещё {len(broken) - 40}")
    if verbose and broken_md:
        for n, t in broken_md[:40]:
            print(f"  {n.rel} -> [{t}]()")
        if len(broken_md) > 40:
            print(f"  ... ещё {len(broken_md) - 40}")

    if out:
        lines = ["# Broken links", "",
                 f"Vault: {input_path}",
                 f"Broken wiki: {len(broken)} в {len(files_with_broken)} файлах",
                 f"Broken markdown: {len(broken_md)} "
                 f"в {len(files_with_broken_md)} файлах", ""]
        cur = None
        for n, t in broken:
            if n.rel != cur:
                cur = n.rel
                lines.append(f"## {cur}")
            lines.append(f"- [[{t}]]")
        if broken_md:
            lines.append("")
            lines.append("# Битые markdown-ссылки")
            cur = None
            for n, t in broken_md:
                if n.rel != cur:
                    cur = n.rel
                    lines.append(f"## {cur}")
                lines.append(f"- {t}")
        write_report(out, "\n".join(lines))
        if str(out).strip() != "-":
            print(f"Отчёт: {out}")
    if json_out:
        write_json(json_out, {
            "tool": "broken-links",
            "input": str(input_path),
            "notes": len(notes),
            "broken_wiki": [{"file": n.rel, "target": t} for n, t in broken],
            "broken_md": [{"file": n.rel, "target": t} for n, t in broken_md],
        })
        print(f"JSON-отчёт: {json_out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Битые вики-ссылки")
    ap.add_argument("--input", required=True, help="путь к vault")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--out", help="файл отчёта")
    ap.add_argument("--json", dest="json_out",
                    help="сохранить отчёт в JSON («-» — в stdout)")
    args = ap.parse_args(argv)
    return run(args.input, limit=args.limit, verbose=args.verbose,
               out=args.out, json_out=args.json_out)


if __name__ == "__main__":
    sys.exit(main())
