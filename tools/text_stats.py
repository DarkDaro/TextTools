# -*- coding: utf-8 -*-
"""
text_stats — статистика текстов (01.10, дешёвая новая вкладка).

Объём (слова/предложения), средняя длина предложения, доля диалогов
(строки, начинающиеся с тире), частотные слова-паразиты (на 1000 слов).
Только читает файлы.

Использование:
  python textools.py stats --input <папка/файл> [--out report.md] [--limit N]
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import text_parser as tp

# классические слова-паразиты и усилители (сравнение без ё, по границам слов)
PARASITES = [
    "просто", "очень", "конечно", "в общем", "как бы", "собственно",
    "на самом деле", "в принципе", "короче", "типа", "как будто",
    "именно", "даже", "вот", "уже", "еще", "только", "потом", "итак",
]
DIALOG_RE = re.compile(r"^\s*[—–-]\s*\S")
WORD_RE = re.compile(r"[А-ЯЁа-яёA-Za-z]+(?:-[А-ЯЁа-яёA-Za-z]+)*")


def analyze_text(text):
    """Словарь со статистикой одного текста."""
    lines = text.splitlines()
    words = WORD_RE.findall(text)
    n_words = len(words)
    sents = [s for s in tp.sentences(text) if s.strip()]
    n_sents = len(sents)
    dialog = sum(1 for ln in lines if DIALOG_RE.match(ln))
    non_empty = sum(1 for ln in lines if ln.strip())
    return {
        "words": n_words,
        "sents": n_sents,
        "avg_sent": round(n_words / n_sents, 1) if n_sents else 0.0,
        "dialog_share": round(100 * dialog / non_empty, 1) if non_empty else 0.0,
        "parasites": _count_parasites(text, n_words),
    }


def _count_parasites(text, n_words):
    """{паразит: (счёт, на_1000_слов)} — регистронезависимо, ё=е."""
    low = tp.norm_yo(text.lower())
    out = {}
    for p in PARASITES:
        pat = re.compile(r"(?<![А-ЯЁа-яёA-Za-z])"
                         + tp.norm_yo(p).replace(" ", r"\s+")
                         + r"(?![А-ЯЁа-яёA-Za-z])", re.IGNORECASE)
        c = len(pat.findall(low))
        if c:
            out[p] = (c, round(1000 * c / n_words, 1) if n_words else 0.0)
    return out


def run(input_path, limit=None, out=None):
    files = list(tp.iter_text_files(input_path, limit=limit))
    total = len(files)
    print(f"PROGRESS:0/{total}", flush=True)

    rows = []  # (файл, статистика)
    totals = {"words": 0, "sents": 0, "dialog_share": 0.0}
    para_total = Counter()
    files_n = 0
    for f in files:
        if tp.stop_requested():
            print("Остановлено пользователем.")
            break
        files_n += 1
        print(f"PROGRESS:{files_n}/{total}", flush=True)
        text = tp.read_text(f)
        if not text:
            continue
        st = analyze_text(text)
        rows.append((f, st))
        totals["words"] += st["words"]
        totals["sents"] += st["sents"]
        totals["dialog_share"] += st["dialog_share"]
        for p, (c, _r) in st["parasites"].items():
            para_total[p] += c

    print(f"\nФайлов: {len(rows)}")
    print(f"{'Файл':<40} {'слов':>6} {'предл.':>7} {'сред.':>6} {'диалог':>7}")
    for f, st in rows[:30]:
        print(f"{Path(f).name[:39]:<40} {st['words']:>6} {st['sents']:>7} "
              f"{st['avg_sent']:>6} {st['dialog_share']:>6}%")
    if len(rows) > 30:
        print(f"  ... ещё {len(rows) - 30}")
    if rows:
        print(f"\nИтого слов: {totals['words']}, предложений: {totals['sents']}, "
              f"средняя длина предложения: "
              f"{round(totals['words'] / totals['sents'], 1) if totals['sents'] else 0}")
        print(f"Средняя доля диалогов: "
              f"{round(totals['dialog_share'] / len(rows), 1)}%")
        if para_total:
            print("\nСлова-паразиты (всего, на 1000 слов по всему корпусу):")
            rate = lambda c: round(1000 * c / totals["words"], 1) if totals["words"] else 0
            for p, c in para_total.most_common(12):
                print(f"  {p}: {c} ({rate(c)}/1000)")
        else:
            print("\nСлова-паразиты не найдены.")

    if out:
        lines = [f"# Статистика текстов — {input_path}", ""]
        lines.append("| Файл | слов | предложений | сред. длина | диалогов, % |")
        lines.append("|---|---|---|---|---|")
        for f, st in rows:
            lines.append(f"| {Path(f).name} | {st['words']} | {st['sents']} | "
                         f"{st['avg_sent']} | {st['dialog_share']} |")
        lines.append("")
        lines.append("## Слова-паразиты")
        rate = lambda c: round(1000 * c / totals["words"], 1) if totals["words"] else 0
        for p, c in para_total.most_common():
            lines.append(f"- {p}: {c} ({rate(c)} на 1000 слов)")
        Path(out).write_text("\n".join(lines), encoding="utf-8")
        print(f"\nОтчёт: {out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Статистика текстов")
    ap.add_argument("--input", required=True, help="папка или файл")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", help="отчёт в .md")
    args = ap.parse_args(argv)
    return run(args.input, limit=args.limit, out=args.out)


if __name__ == "__main__":
    sys.exit(main())
