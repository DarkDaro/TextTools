"""
merge_finder — кандидаты на слияние: дубликаты по содержимому (хеш)
и заметки с одинаковым именем файла в разных папках.

  python textools.py merge-finder --input <vault> [--out report.md]
      [--limit N] [--verbose]
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import vault_scanner as vs


def run(input_path, limit=None, verbose=False, out=None):
    notes, basenames, relpaths = vs.scan_vault(input_path, limit=limit)

    # 1. точные дубликаты по нормализованному содержимому
    by_hash = {}
    for n in notes:
        if n.hash:
            by_hash.setdefault(n.hash, []).append(n)
    dup_content = [(h, g) for h, g in by_hash.items() if len(g) > 1]

    # 2. одинаковые имена файлов в разных папках
    by_stem = {}
    for n in notes:
        by_stem.setdefault(n.stem, []).append(n)
    dup_names = [(s, g) for s, g in by_stem.items() if len(g) > 1]

    print(f"Заметок: {len(notes)}")
    print(f"Дубликатов по содержимому: {len(dup_content)} групп")
    print(f"Одинаковых имён в разных папках: {len(dup_names)} групп")

    if verbose:
        for h, g in dup_content[:15]:
            print(f"  [{h[:8]}]")
            for n in g:
                print(f"    {n.rel}")
        for s, g in dup_names[:15]:
            print(f"  \"{s}\" x{len(g)}:")
            for n in g:
                print(f"    {n.rel}")

    if out:
        lines = ["# Merge candidates", "",
                 f"Vault: {input_path}", "",
                 f"## Дубликаты по содержимому: {len(dup_content)} групп", ""]
        for h, g in dup_content:
            lines.append(f"- [{h[:8]}]")
            for n in g:
                lines.append(f"  - {n.rel}")
        lines += ["", f"## Одинаковые имена: {len(dup_names)} групп", ""]
        for s, g in dup_names:
            lines.append(f"- \"{s}\" ({len(g)} шт.)")
            for n in g:
                lines.append(f"  - {n.rel}")
        Path(out).write_text("\n".join(lines), encoding="utf-8")
        print(f"Отчёт: {out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Кандидаты на слияние")
    ap.add_argument("--input", required=True, help="путь к vault")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--out", help="файл отчёта")
    args = ap.parse_args(argv)
    return run(args.input, limit=args.limit, verbose=args.verbose, out=args.out)