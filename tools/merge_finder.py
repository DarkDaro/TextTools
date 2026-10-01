"""
merge_finder — кандидаты на слияние: дубликаты по содержимому (хеш)
и заметки с одинаковым именем файла в разных папках.

  python textools.py merge-finder --input <vault> [--out report.md]
      [--limit N] [--verbose]
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import vault_scanner as vs
from core import text_parser as tp

# 01.10: близкие дубликаты — 5-словные шинглы и коэффициент Жаккара
SHINGLE_N = 5
NEAR_THRESHOLD = 0.7
NEAR_CAP = 1500  # сравниваем не больше N заметок (иначе слишком долго)

_SHINGLE_RE = re.compile(r"[А-ЯЁа-яёA-Za-z]+")


def _shingles(text):
    words = [tp.norm_yo(w.lower()) for w in _SHINGLE_RE.findall(text or "")]
    if len(words) < 15:  # слишком короткие заметки не сравниваем
        return None
    return {tuple(words[i:i + SHINGLE_N]) for i in range(len(words) - SHINGLE_N + 1)}


def near_duplicates(notes, threshold=NEAR_THRESHOLD):
    """[(заметка А, заметка Б, жаккар)] — почти одинаковые по содержимому.
    02.10 (СЛ7): инвертированный индекс «шингл -> заметки» — сравниваются
    только пары с общими шинглами, а не все пары подряд (O(n^2) множеств)."""
    sh = []
    for n in notes:
        s = _shingles(_note_text(n))
        if s:
            sh.append((n, s))
    sh = sh[:NEAR_CAP]

    index = {}
    for i, (_n, s) in enumerate(sh):
        for shingle in s:
            index.setdefault(shingle, []).append(i)

    out = []
    total = len(sh)
    print(f"PROGRESS:0/{total}", flush=True)
    for i, (_n, s) in enumerate(sh):  # индексация 0-базовая — как в index
        print(f"PROGRESS:{i + 1}/{total}", flush=True)
        seen = {}
        for shingle in s:
            for j in index.get(shingle, ()):
                if j < i:  # каждая пара один раз
                    seen[j] = seen.get(j, 0) + 1
        for j, inter in seen.items():
            a, b = sh[i][1], sh[j][1]
            jac = inter / (len(a) + len(b) - inter)
            if jac >= threshold:
                out.append((sh[j][0], sh[i][0], round(jac, 2)))
    out.sort(key=lambda t: -t[2])
    return out


def _note_text(note):
    try:
        return note.path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError, OSError):
        from core import encoding as _enc
        t, _e = _enc.read_any(note.path)
        return t or ""


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

    # 3. близкие дубликаты (шинглы/Жаккар, 01.10)
    dups_exact = {n for _, g in dup_content for n in g}
    near = [(a, b, j) for a, b, j in near_duplicates(notes)
            if a not in dups_exact or b not in dups_exact]

    print(f"Заметок: {len(notes)}")
    print(f"Дубликатов по содержимому: {len(dup_content)} групп")
    print(f"Одинаковых имён в разных папках: {len(dup_names)} групп")
    print(f"Близких дубликатов (>= {NEAR_THRESHOLD:.0%}): {len(near)} пар")

    if verbose and near:
        print(f"  Ближайшие пары:")
        for a, b, j in near[:15]:
            print(f"    {j:.0%}  {a.rel}  <->  {b.rel}")

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
        lines += ["", f"## Близкие дубликаты: {len(near)} пар", ""]
        for a, b, j in near:
            lines.append(f"- {j:.0%}: {a.rel} <-> {b.rel}")
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