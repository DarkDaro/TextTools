"""
broken_links — вики-ссылки на несуществующие заметки.

  python textools.py broken-links --input <vault> [--out report.md]
      [--limit N] [--verbose]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import vault_scanner as vs


def run(input_path, limit=None, verbose=False, out=None):
    notes, basenames, relpaths = vs.scan_vault(input_path, limit=limit)

    broken = []  # (note, target)
    for n in notes:
        for t in sorted(n.links):
            if not vs.is_resolved(t, basenames, relpaths):
                broken.append((n, t))

    files_with_broken = sorted({n.rel for n, _ in broken})
    print(f"Заметок: {len(notes)}")
    print(f"Битых ссылок: {len(broken)} в {len(files_with_broken)} файлах")

    if verbose and broken:
        for n, t in broken[:40]:
            print(f"  {n.rel} -> [[{t}]]")
        if len(broken) > 40:
            print(f"  ... ещё {len(broken) - 40}")

    if out:
        lines = ["# Broken links", "",
                 f"Vault: {input_path}",
                 f"Broken: {len(broken)} в {len(files_with_broken)} файлах", ""]
        cur = None
        for n, t in broken:
            if n.rel != cur:
                cur = n.rel
                lines.append(f"## {cur}")
            lines.append(f"- [[{t}]]")
        Path(out).write_text("\n".join(lines), encoding="utf-8")
        print(f"Отчёт: {out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Битые вики-ссылки")
    ap.add_argument("--input", required=True, help="путь к vault")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--out", help="файл отчёта")
    args = ap.parse_args(argv)
    return run(args.input, limit=args.limit, verbose=args.verbose, out=args.out)