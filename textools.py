"""
textools — единый CLI текстовых инструментов.

Команды:
  registry-builder   найти имена-кандидаты в текстах
  consistency        проверить имена по реестру (старые/опасные/опечатки)
  orphan-finder      заметки без входящих и исходящих ссылок
  broken-links       вики-ссылки на несуществующие заметки
  merge-finder       дубликаты по содержимому и по именам файлов
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import argparse


def main():
    ap = argparse.ArgumentParser(description="textools: инструменты для текста")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("registry-builder",
                        help="найти имена-кандидаты в текстах")
    p1.add_argument("--input", required=True)
    p1.add_argument("--out")
    p1.add_argument("--registry")
    p1.add_argument("--min-count", type=int, default=2)
    p1.add_argument("--limit", type=int)
    p1.add_argument("--verbose", action="store_true")

    p2 = sub.add_parser("consistency",
                        help="проверка имён по реестру")
    p2.add_argument("--input", required=True)
    p2.add_argument("--registry", required=True)
    p2.add_argument("--limit", type=int)
    p2.add_argument("--verbose", action="store_true")
    p2.add_argument("--out")

    # 01.10: новые инструменты
    p3 = sub.add_parser("forms",
                        help="недостающие падежные формы реестра (pymorphy3)")
    p3.add_argument("--registry", required=True)
    p3.add_argument("--fill", action="store_true",
                    help="дописать формы в реестр (с .bak)")
    p3.add_argument("--out")

    p4 = sub.add_parser("utf8", help="проверка/приведение текстов к UTF-8")
    p4.add_argument("--input", required=True)
    p4.add_argument("--fix", action="store_true")
    p4.add_argument("--limit", type=int)

    p5 = sub.add_parser("matrix", help="матрица «персонаж × файл»")
    p5.add_argument("--input", required=True)
    p5.add_argument("--registry", required=True)
    p5.add_argument("--limit", type=int)
    p5.add_argument("--verbose", action="store_true")
    p5.add_argument("--out")

    p6 = sub.add_parser("merge-registry",
                        help="добавить кандидатов в реестр персонажей")
    p6.add_argument("--candidates", required=True)
    p6.add_argument("--registry", required=True)
    p6.add_argument("--names", help="только эти имена (через запятую)")
    p6.add_argument("--add", action="store_true", help="реально дописать (с .bak)")

    p7 = sub.add_parser("restore", help="обзор/восстановление из бэкапов")
    p7.add_argument("--input", required=True)
    p7.add_argument("--restore", action="store_true")
    p7.add_argument("--file", help="только этот файл (по имени)")

    p8 = sub.add_parser("stats", help="статистика текстов (объём, диалоги, паразиты)")
    p8.add_argument("--input", required=True)
    p8.add_argument("--limit", type=int)
    p8.add_argument("--out")
    p8.add_argument("--csv", action="store_true",
                    help="дописать строку в reports/stats_log.csv (дневник объёма)")

    p9 = sub.add_parser("archive-backups",
                        help="архивация старых бэкапов (перенос в archive/backups)")
    p9.add_argument("--input", required=True)
    p9.add_argument("--days", type=int, default=30)
    p9.add_argument("--move", action="store_true")

    p10 = sub.add_parser("moc", help="MOC-заметки персонажей для Obsidian")
    p10.add_argument("--input", required=True)
    p10.add_argument("--registry", required=True)
    p10.add_argument("--out-dir", required=True)
    p10.add_argument("--limit", type=int)
    p10.add_argument("--apply", action="store_true")
    p10.add_argument("--update", action="store_true")

    for name, desc in (("orphan-finder", "заметки без входящих и исходящих ссылок"),
                       ("broken-links", "вики-ссылки на несуществующие заметки"),
                       ("merge-finder", "дубликаты по содержимому и по именам")):
        p = sub.add_parser(name, help=desc)
        p.add_argument("--input", required=True)
        p.add_argument("--limit", type=int)
        p.add_argument("--verbose", action="store_true")
        p.add_argument("--out")

    p11 = sub.add_parser("typography",
                         help="типографика: «ёлочки», тире, многоточия (с .bak)")
    p11.add_argument("--input", required=True)
    p11.add_argument("--fix", action="store_true",
                     help="реально править (по умолчанию dry-run)")
    p11.add_argument("--nbsp", action="store_true",
                     help="неразрывные пробелы после предлогов и «№»")
    p11.add_argument("--out")

    p12 = sub.add_parser("style-report",
                         help="стилистика: повторы слов рядом, длинные предложения")
    p12.add_argument("--input", required=True)
    p12.add_argument("--registry", help="реестр персонажей (исключить их формы)")
    p12.add_argument("--window", type=int, default=5,
                     help="окно повтора в словах (по умолчанию 5)")
    p12.add_argument("--long", type=int, default=25,
                     help="порог длинного предложения в словах (по умолчанию 25)")
    p12.add_argument("--limit", type=int)
    p12.add_argument("--out")

    args = ap.parse_args()

    here = Path(__file__).parent
    simple = {"orphan-finder": "orphan_finder",
              "broken-links": "broken_links",
              "merge-finder": "merge_finder"}
    if args.cmd in simple:
        sys.path.insert(0, str(here))
        mod = __import__(f"tools.{simple[args.cmd]}", fromlist=["run"])
        opts = ["--input", args.input,
                *(["--limit", str(args.limit)] if args.limit else []),
                *(["--verbose"] if args.verbose else []),
                *(["--out", args.out] if args.out else [])]
        sys.exit(mod.main(opts))
    if args.cmd == "merge-registry":
        sys.path.insert(0, str(here))
        from tools import registry_merge
        registry_merge.main(
            ["--candidates", args.candidates, "--registry", args.registry,
             *(["--names", args.names] if args.names else []),
             *(["--add"] if args.add else [])])
    elif args.cmd == "archive-backups":
        sys.path.insert(0, str(here))
        from tools import backup_archive
        backup_archive.main(
            ["--input", args.input, "--days", str(args.days),
             *(["--move"] if args.move else [])])
    elif args.cmd == "moc":
        sys.path.insert(0, str(here))
        from tools import moc_builder
        moc_builder.main(
            ["--input", args.input, "--registry", args.registry,
             "--out-dir", args.out_dir,
             *(["--limit", str(args.limit)] if args.limit else []),
             *(["--apply"] if args.apply else []),
             *(["--update"] if args.update else [])])
    elif args.cmd == "stats":
        sys.path.insert(0, str(here))
        from tools import text_stats
        text_stats.main(
            ["--input", args.input,
             *(["--limit", str(args.limit)] if args.limit else []),
             *(["--out", args.out] if args.out else []),
             *(["--csv"] if args.csv else [])])
    elif args.cmd == "typography":
        sys.path.insert(0, str(here))
        from tools import typography
        typography.main(
            ["--input", args.input, *(["--fix"] if args.fix else []),
             *(["--nbsp"] if args.nbsp else []),
             *(["--out", args.out] if args.out else [])])
    elif args.cmd == "style-report":
        sys.path.insert(0, str(here))
        from tools import style_report
        style_report.main(
            ["--input", args.input,
             *(["--registry", args.registry] if args.registry else []),
             "--window", str(args.window), "--long", str(args.long),
             *(["--limit", str(args.limit)] if args.limit else []),
             *(["--out", args.out] if args.out else [])])
    elif args.cmd == "restore":
        sys.path.insert(0, str(here))
        from tools import backup_restore
        backup_restore.main(
            ["--input", args.input, *(["--restore"] if args.restore else []),
             *(["--file", args.file] if args.file else [])])
    elif args.cmd == "forms":
        sys.path.insert(0, str(here))
        from tools import morph_forms
        morph_forms.main(
            ["--registry", args.registry,
             *(["--fill"] if args.fill else []),
             *(["--out", args.out] if args.out else [])])
    elif args.cmd == "utf8":
        sys.path.insert(0, str(here))
        from tools import utf8_convert
        utf8_convert.main(
            ["--input", args.input, *(["--fix"] if args.fix else []),
             *(["--limit", str(args.limit)] if args.limit else [])])
    elif args.cmd == "matrix":
        sys.path.insert(0, str(here))
        from tools import character_matrix
        character_matrix.main(
            ["--input", args.input, "--registry", args.registry,
             *(["--limit", str(args.limit)] if args.limit else []),
             *(["--verbose"] if args.verbose else []),
             *(["--out", args.out] if args.out else [])])
    elif args.cmd == "registry-builder":
        sys.path.insert(0, str(here))
        from tools import registry_builder
        registry_builder.main(
            ["--input", args.input, *(["--out", args.out] if args.out else []),
             *(["--registry", args.registry] if args.registry else []),
             "--min-count", str(args.min_count),
             *(["--limit", str(args.limit)] if args.limit else []),
             *(["--verbose"] if args.verbose else [])])
    elif args.cmd == "consistency":
        sys.path.insert(0, str(here))
        from tools import consistency
        consistency.main(
            ["--input", args.input, "--registry", args.registry,
             *(["--limit", str(args.limit)] if args.limit else []),
             *(["--verbose"] if args.verbose else []),
             *(["--out", args.out] if args.out else [])])


if __name__ == "__main__":
    main()