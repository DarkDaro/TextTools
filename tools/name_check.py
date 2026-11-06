# -*- coding: utf-8 -*-
"""
name_check — проверка придуманного имени/названия на занятость (07.11).

  python textools.py name-check --name "Nebula" [--out отчёт.md]

Оффлайн-проверка БЕЗ сети: сверяет название со встроенным справочником
известных приложений, брендов и часто используемых проектных слов
(data/name_alerts.yaml), плюс эвристики риска. Сеть тут не нужна:
цель — поймать очевидные совпадения и заставить проверить спорное
вручную, а не выносить юридический вердикт.

В отчёте — вердикт риска, совпадения и готовый абзац-дисклеймер,
который можно вставить в книгу.
"""
import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.report import write_report

ALERTS_FILE = Path(__file__).resolve().parent.parent / "data" / "name_alerts.yaml"

DISCLAIMER = (
    "Все персонажи, организации, технологии, названия мест и события, "
    "описанные в этой книге, вымышлены. Любое сходство с реальными "
    "людьми, компаниями, товарами или событиями случайно и не "
    "имело целью очернить или использовать чьё-либо имя.")

CHECKS = (
    "1. Поиск по магазинам приложений (App Store, Google Play, RuStore) "
    "и по GitHub — совпадение с чужим приложением.",
    "2. Поиск по поисковику в кавычках: «Название» книга, «Название» "
    "бренд.",
    "3. База товарных знаков Роспатента/ФИПС (проверка классов 9, 16, "
    "41 — софт, книги, издательская деятельность).",
    "4. Домены: занят ли site.ru у названия в латинице.",
)


def load_alerts():
    try:
        data = yaml.safe_load(ALERTS_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    # {имя: категория}
    out = {}
    for cat, names in data.items():
        for n in names or []:
            out[str(n).strip().lower()] = cat
    return out


def check(name, alerts=None):
    """[(совпадение, категория, вид)] + вердикт риска.

    вид: exact — полное совпадение; contains — название содержит
    известное слово длиной 5+ символов."""
    alerts = alerts if alerts is not None else load_alerts()
    low = name.strip().lower()
    hits = []
    if not low:
        return hits, "пусто"
    if low in alerts:
        hits.append((low, alerts[low], "exact"))
    for entry, cat in alerts.items():
        if entry == low:
            continue
        if len(entry) >= 5 and (entry in low or low in entry):
            hits.append((entry, cat, "contains"))
    # вердикт
    if any(h[2] == "exact" for h in hits):
        verdict = "высокий риск: точное совпадение с известным названием"
    elif low.isascii() and low.isalpha() and len(low.split()) == 1 \
            and len(low) <= 12:
        verdict = ("повышенный риск: короткое латинское слово — такие "
                   "названия почти всегда уже заняты приложениями/проектами")
    elif len(low.split()) == 1 and len(low) >= 5 and not low.isascii():
        verdict = ("средний: одиночное слово — проверь товарные знаки "
                   "и выдачу поисковика")
    else:
        verdict = ("низкий: составное или выдуманное название; "
                   "быструю проверку всё равно стоит пройти")
    return hits, verdict


def run(name, out=None):
    alerts = load_alerts()
    hits, verdict = check(name, alerts)
    print(f"Проверка имени: «{name}»")
    print(f"Вердикт: {verdict}")
    if hits:
        print("Совпадения со справочником:")
        for entry, cat, kind in hits:
            tag = "точное" if kind == "exact" else "частичное"
            print(f"  «{entry}» — {cat} ({tag})")
    else:
        print("Совпадений со встроенным справочником нет.")
    print("\nКак проверить до печати книги:")
    for c in CHECKS:
        print(f"  {c}")
    print("\nДисклеймер для книги (можно копировать в титул):")
    print(f"  {DISCLAIMER}")
    if out:
        L = [f"# Проверка имени — «{name}»", "", f"**Вердикт:** {verdict}.", ""]
        if hits:
            L.append("| Совпадение | Категория | Вид |")
            L.append("|---|---|---|")
            for entry, cat, kind in hits:
                tag = "точное" if kind == "exact" else "частичное"
                L.append(f"| {entry} | {cat} | {tag} |")
        else:
            L.append("Совпадений со встроенным справочником нет.")
        L += ["", "## Как проверить до печати книги", ""]
        L += [f"- {c}" for c in CHECKS]
        L += ["", "## Дисклеймер для книги", "", DISCLAIMER]
        write_report(out, "\n".join(L))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Проверка придуманного имени на занятость (оффлайн)")
    ap.add_argument("--name", required=True, help="имя/название для проверки")
    ap.add_argument("--out", help="файл отчёта")
    args = ap.parse_args(argv)
    return run(args.name, out=args.out)


if __name__ == "__main__":
    sys.exit(main())
