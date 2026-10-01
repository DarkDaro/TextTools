"""
01_registry_builder — построение реестра имён.
Сканирует тексты, находит слова с заглавной буквы в середине предложения
и пары «Имя Фамилия». Выводит сводку, по --out сохраняет кандидатов в YAML.

Использование:
  python textools.py registry-builder --input <файл/папка> [--out candidates.yaml]
      [--registry characters.yaml] [--min-count 2] [--limit N] [--verbose]
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import morph
from core import text_parser as tp
from core import name_registry as nr


def run(input_path, out=None, registry=None, min_count=2, limit=None,
        verbose=False):
    chars = nr.load_registry(registry) if registry else []
    known = nr.known_forms(chars)
    known_titles = nr.known_first_names(chars)
    # 01.10: известными считаются и падежные формы (pymorphy3) — иначе
    # «Эрикой» предлагалась как новый кандидат
    if morph.AVAILABLE and known:
        known = set(known) | {f for w in list(known)
                              for f in morph.word_forms(w)}

    uni = Counter()
    bi = Counter()
    files_n = 0
    for path in tp.iter_text_files(input_path, limit=limit):
        text = tp.read_text(path)
        if not text:
            continue
        files_n += 1
        for w in tp.find_name_candidates(text, known=known):
            uni[w] += 1
        for bg in tp.find_bigrams(text, known=known):
            # второй компонент bigram — главный кандидат (имя),
            # если второй компонент - известный титул, пропускаем пару
            if bg.split()[0] not in known_titles:
                bi[bg] += 1
            else:
                uni[bg.split()[1]] += 1

    # фильтр по частоте
    uni = {w: c for w, c in uni.items() if c >= min_count}
    bi = {w: c for w, c in bi.items() if c >= min_count}

    print(f"Файлов просканировано: {files_n}")
    print(f"Кандидаты-слова (частота >= {min_count}): {len(uni)}")
    print(f"Кандидаты-пары (частота >= {min_count}): {len(bi)}")
    print()
    print("ТОП-20 кандидатов-слов:")
    for w, c in sorted(uni.items(), key=lambda x: -x[1])[:20]:
        print(f"  {w}: {c}")
    print()
    print("ТОП-10 кандидатов-пар:")
    for w, c in sorted(bi.items(), key=lambda x: -x[1])[:10]:
        print(f"  {w}: {c}")

    if out:
        items = ([{"имя": w, "формы": [w], "встречается": c}
                  for w, c in sorted(uni.items(), key=lambda x: -x[1])]
                 + [{"имя": w, "формы": [w], "пар": c, "составное": True}
                    for w, c in sorted(bi.items(), key=lambda x: -x[1])])
        nr.save_registry(out, items)
        print(f"\nСохранено: {out}")
        if verbose:
            for it in items[:40]:
                extra = f" (пар: {it.get('пар')})" if it.get("пар") else ""
                print(f"  {it['имя']}: {it['встречается']}{extra}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Поиск имён-кандидатов в текстах")
    ap.add_argument("--input", required=True, help="файл или папка .md/.txt/.docx")
    ap.add_argument("--out", help="сохранить кандидатов в YAML файл")
    ap.add_argument("--registry", help="существующий реестр (исключить его имена)")
    ap.add_argument("--min-count", type=int, default=2)
    ap.add_argument("--limit", type=int, help="обработать не больше N файлов")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)
    return run(args.input, out=args.out, registry=args.registry,
               min_count=args.min_count, limit=args.limit, verbose=args.verbose)