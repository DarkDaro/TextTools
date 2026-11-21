# -*- coding: utf-8 -*-
"""
cast_list — список персонажей без повторов в текстовый лог (07.11).

  python textools.py cast --input <папка/файл> [--registry characters.yaml]
      [--min-count 1] [--out reports/cast_list.txt] [--lang ru|en]

Собирает все имена с заглавной буквы из .md/.txt/.docx/.html, убирает
повторы, считает вхождения и пишет текстовый лог: сколько персонажей,
кто чаще всех встречается, пары «Имя Фамилия» и места, где одно имя
пишется по-разному (Семён/Семен) — это и есть ошибки в именах.

Польза: одна страница — и видно весь состав книги и грязь в именах.
Реестр (--registry) не обязателен: инструмент сам находит всех.

18.11: язык текстов (docs/LOC_PLAN.md). Для английского — свои
регэкспы имён (латиница, дефис, апостроф) и свой стоп-лист; титулы
и месяцы отсеиваются даже в середине предложения (the Captain —
не имя). По умолчанию язык берётся из настроек (ключ text_lang),
флаг --lang переопределяет.
"""
import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import lang as lang_mod
from core import text_parser as tp
from core.report import write_report

# Имя: заглавная + строчные, возможно через дефис (Анна-Мария).
# АББРЕВИАТУРЫ (СВГ, ОБС) отсечены: после заглавной обязательны строчные.
RE_NAME = re.compile(r"\b[А-ЯЁ][а-яё]+(?:-[а-яё]+)?")
RE_PAIR = re.compile(r"\b([А-ЯЁ][а-яё]+) ([А-ЯЁ][а-яё]+)\b")

# 18.11: английское имя — латиница; дефис и апостроф внутри имени
# допустимы (Anne-Marie, O’Brian для стартера ловится как Brien —
# граница апострофа уточнится по практике).
RE_NAME_EN = re.compile(r"\b[A-Z][a-z]+(?:[-‘’][A-Z][a-z]+)*")
RE_PAIR_EN = re.compile(
    r"\b([A-Z][a-z]+(?:[-‘’][A-Z][a-z]+)*)"
    r" ([A-Z][a-z]+(?:[-‘’][A-Z][a-z]+)*)\b")

DEFAULT_OUT = Path("reports") / "cast_list.txt"


def _regexes(is_en):
    return (RE_NAME_EN, RE_PAIR_EN) if is_en else (RE_NAME, RE_PAIR)


def scan_text(text, lang=None):
    """(одиночные имена, пары «Имя Фамилия») со счётчиками.

    Шум отсекается так: имя считается «настоящим», если встретилось
    не только в начале предложения. Служебные слова не попадают в
    кандидаты вовсе. Для английского строже: титул, месяц или день
    недели с заглавной в середине предложения (the Captain) — тоже
    не имя, отсекается всегда.

    lang: «ru»/«en»; None — из настроек (text_lang в gui_config.json)."""
    if lang is None:
        lang = lang_mod.get_text_lang(None)
    is_en = lang_mod.is_en(lang)
    re_name, re_pair = _regexes(is_en)
    stops = tp.stoplist(lang)
    single = Counter()
    mid = Counter()          # в середине предложения — сильный сигнал
    pairs = Counter()
    for sent in tp.sentences(text):
        words = re_name.findall(sent)
        for i, w in enumerate(words):
            single[w] += 1
            if i > 0:
                mid[w] += 1
        for a, b in re_pair.findall(sent):
            pairs[f"{a} {b}"] += 1
    # отсеиваем: для en — служебные всегда; для ru — как раньше,
    # только если имя не встречалось в середине предложения
    for w in list(single):
        low = tp.norm_yo(w.lower())
        if low in stops and (is_en or mid[w] == 0):
            del single[w]
    return single, pairs


def collect(input_path):
    root = tp.check_root(input_path)
    if root.is_file():
        return [root] if root.suffix.lower() in tp.ANALYSIS_EXTS else []
    return list(tp.iter_text_files(root, exts=tp.ANALYSIS_EXTS))


def run(input_path, out=None, min_count=1, lang=None):
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
        s, p = scan_text(text, lang)
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
    write_report(out_path, "\n".join(L) + "\n")  # «-» = stdout (21.11)
    if str(out_path).strip() != "-":
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
    ap.add_argument("--lang", choices=lang_mod.LANGS,
                    help="язык текстов (по умолчанию — из настроек)")
    args = ap.parse_args(argv)
    return run(args.input, out=args.out, min_count=args.min_count,
               lang=args.lang)


if __name__ == "__main__":
    sys.exit(main())
