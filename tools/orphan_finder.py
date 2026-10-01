"""
orphan_finder — заметки без входящих и исходящих ссылок.

  python textools.py orphan-finder --input <vault> [--out report.md]
      [--limit N] [--verbose]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import vault_scanner as vs


def build_incoming(notes, basenames, relpaths):
    """01.10 (СЛ7): set заметок, на которые есть хотя бы одна входящая
    ссылка. O(всех ссылок) вместо O(n^2) попарных проверок."""
    by_target = {}
    for n in notes:
        by_target.setdefault(str(n.rel).removesuffix(".md").lower(), n)
    has_incoming = set()
    for n in notes:
        for t in n.links:
            target = by_target.get(t) or by_target.get(t.rsplit("/", 1)[-1])
            if target is not None and target is not n:
                has_incoming.add(target)
    return has_incoming


def run(input_path, limit=None, verbose=False, out=None):
    notes, basenames, relpaths = vs.scan_vault(input_path, limit=limit)
    has_incoming = build_incoming(notes, basenames, relpaths)
    orphans = [n for n in notes
               if not n.links  # нет исходящих
               and n not in has_incoming]
    print(f"Заметок: {len(notes)}")
    print(f"Orphan (нет входящих и исходящих ссылок): {len(orphans)}")

    if verbose and orphans:
        for n in orphans[:40]:
            print(f"  {n.rel}")
        if len(orphans) > 40:
            print(f"  ... ещё {len(orphans) - 40}")

    if out:
        lines = ["# Orphan notes", "",
                 f"Vault: {input_path}", f"Orphans: {len(orphans)}", ""]
        for n in orphans:
            lines.append(f"- {n.rel}")
        Path(out).write_text("\n".join(lines), encoding="utf-8")
        print(f"Отчёт: {out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Orphan-заметки без ссылок")
    ap.add_argument("--input", required=True, help="путь к vault")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--out", help="файл отчёта")
    args = ap.parse_args(argv)
    return run(args.input, limit=args.limit, verbose=args.verbose, out=args.out)