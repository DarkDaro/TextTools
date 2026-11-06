# -*- coding: utf-8 -*-
"""
cast_list — список персонажей без повторов в текстовый лог (07.11).

  python textools.py cast --input <папка/файл> [--registry characters.yaml]
      [--min-count 1] [--out reports/cast_list.txt]

Собирает все имена с заглавной буквы из .md/.txt/.docx/.html, убирает
повторы, считает вхождения и пишет текстовый лог: сколько персонажей,
кто чаще всех встречается, пары «Имя Фамилия» и места, где одно имя
пишется по-разному (Семён/Семен) — это и есть ошибки в именах.

Польза: одна страница — и видно весь состав книги и грязь в именах.
Реестр (--registry) не обязателен: инструмент сам находит всех.
"""
import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import text_parser as tp

# Имя: заглавная + строчные, возможно через дефис (Анна-Мария).
# АББРЕВИАТУРЫ (СВГ, ОБС) отсечены: после заглавной обязательны строчные.
RE_NAME = re.compile(r"\b[А-ЯЁ][а-яё]+(?:-[а-яё]+)?")
RE_PAIR = re.compile(r"\b([А-ЯЁ][а-яё]+) ([А-ЯЁ][а-яё]+)\b")

DEFAULT_OUT = Path("reports") / "cast_list.txt"


def scan_text(text):
    """(одиночные имена, пары «Имя Фамилия») со счётчиками.

    Шум отсекается так: имя считается «настоящим», если встретилось
    не только в начале предложения. Служебные слова (tp.STOPLIST) не
    попадают в кандидаты вовсе."""
    single = Counter()
    mid = Counter()          # в середине предложения — сильный сигнал
    pairs = Counter()
    for sent in tp.sentences(text):
        words = RE_NAME.findall(sent)
        for i, w in enumerate(words):
            single[w] += 1
            if i > 0:
                mid[w] += 1
        for a, b in RE_PAIR.findall(sent):
            pairs[f"{a} {b}"] += 1
    # отсеиваем: только начало предложения и в списке служебных
    for w in list(single):
        if mid[w] == 0:
            low = tp.norm_yo(w.lower())
            if low in tp.STOPLIST:
                del single[w]
    return single, pairs


def collect(input_path):
    root = tp.check_root(input_path)
    if root.is_file():
        return [root] if root.suffix.lower() in tp.ANALYSIS_EXTS else []
    return list(tp.iter_text_files(root, exts=tp.ANALYSIS_EXTS))


def run(input_path, out=None, min_count=1):
    try:
        files = collect(input_path)
    except ValueError as e:  # 07.11: пустой/несуществующий путь — не падаем
        print(f"Ошибка: {e}")
        return 1
    if not files:
        print("Файлы .md/.txt/.docx/.html не найдены.")
        return 1
    single, pairs = Counter(), Counter()
    total = len(files)
    print(f"PROGRESS:0/{total}", flush=True)
    for idx, f in enumerate(files, 1):
        if tp.stop_requested():
            print("Остановлено пользователем.")
            break
        text = tp.read_text(f)
        if not text:
            continue
        s, p = scan_text(text)
        single.update(s)
        pairs.update(p)
        print(f"PROGRESS:{idx}/{total}", flush=True)

    # одно имя, разные написания (ё/е и опечатки): группа по ё-норме
    groups = defaultdict(set)
    for w in single:
        groups[tp.norm_yo(w.lower())].add(w)
    variants = {base: sorted(sp, key=lambda x: -single[x])
                for base, sp in groups.items() if len(sp) > 1}

    names = sorted(((w, c) for w, c in single.items() if c >= min_count),
                   key=lambda x: (-x[1], x[0]))
    top_pairs = pairs.most_common(30)

    print(f"\nУникальных имён: {len(names)} (порог {min_count}+ вхождений)")
    for w, c in names[:30]:
        print(f"  {w} — {c}")
    if len(names) > 30:
        print(f"  ... ещё {len(names) - 30} — в логе")
    if top_pairs:
        print("\nПары «Имя Фамилия» (топ): "
              + ", ".join(f"{p} ({c})" for p, c in top_pairs[:10]))
    if variants:
        print("\nВОЗМОЖНЫЕ ОШИБКИ — одно имя пишется по-разному:")
        for base, sp in variants.items():
            print("  " + ", ".join(f"{w} ({single[w]})" for w in sp))

    # лог — по умолчанию reports/cast_list.txt (--out переопределяет)
    out_path = Path(out) if out else DEFAULT_OUT
    out_path.parent.mkdir(parents=True, exist_ok=True)
    L = [f"# Персонажи — {input_path}",
         f"Дата: уникальных имён {len(names)}; "
         f"пар «Имя Фамилия» {len(pairs)}.", "",
         "## Имена (по убыванию вхождений)", ""]
    for w, c in names:
        L.append(f"{w} — {c}")
    L += ["", "## Пары «Имя Фамилия»", ""]
    for p, c in top_pairs:
        L.append(f"{p} — {c}")
    if variants:
        L += ["", "## Возможные ошибки: одно имя пишется по-разному", ""]
        for base, sp in variants.items():
            L.append(" / ".join(f"{w} ({single[w]})" for w in sp))
    out_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nЛог: {out_path}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Список персонажей без повторов в текстовый лог")
    ap.add_argument("--input", required=True,
                    help="папка или файл .md/.txt/.docx/.html")
    ap.add_argument("--out", help=f"лог (по умолчанию {DEFAULT_OUT})")
    ap.add_argument("--min-count", type=int, default=1,
                    help="минимум вхождений (по умолчанию 1 — все)")
    args = ap.parse_args(argv)
    return run(args.input, out=args.out, min_count=args.min_count)


if __name__ == "__main__":
    sys.exit(main())
