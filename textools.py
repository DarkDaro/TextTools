"""
textools — единый CLI текстовых инструментов.

Команды:
  registry-builder   найти имена-кандидаты в текстах
  consistency        проверить имена по реестру (старые/опасные/опечатки)
  forms              недостающие падежные формы реестра (pymorphy3)
  merge-registry     добавить кандидатов в реестр персонажей
  matrix             матрица «персонаж × файл»
  moc                MOC-заметки персонажей для Obsidian
  orphan-finder      заметки без входящих и исходящих ссылок
  broken-links       вики-ссылки на несуществующие заметки
  merge-finder       дубликаты по содержимому и по именам файлов
  integrity          целостность .md: пустые, битый UTF-8, frontmatter, заголовки
  obsidian-check     валидатор метафайлов Obsidian: таблицы, заголовки, теги, ссылки
  cjk                иероглифы (CJK), мойбейк и порча кодировки (только чтение)
  utf8               проверка/приведение текстов к UTF-8
  typography         типографика: «ёлочки», тире, многоточия
  style-report       стилистика: повторы слов рядом, длинные предложения
  stats              статистика текстов (объём, диалоги, паразиты)
  whitespace         чистка пробелов и пустых строк
  separators         чистка мусорных разделителей (///// **** =====)
  phrase-check       поиск и чистка фраз-штампов (--clean из консоли)
  yo                 ё/е-аудит: словарные пары, омографы, имена из реестра
  export-docx        глава .md → Word .docx (для беты и редакторов)
  check-all          профиль «проверить всё»: 6 проверок одним прогоном
  antiresolve        АНТИРЕШИМОСТЬ: поиск/зачистка лексики и пафоса романа
  emoji-icons        эмодзи-иконки → SVG в HTML
  restore            обзор/восстановление из бэкапов
  archive-backups    архивация старых бэкапов
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import argparse

# 24.10: версия проекта — единый источник для CLI, GUI и pyproject.toml
__version__ = "1.0.0"


def main():
    ap = argparse.ArgumentParser(description="textools: инструменты для текста")
    ap.add_argument("--version", action="version",
                    version=f"textools {__version__}")
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
    p4.add_argument("--json", dest="json_out",
                    help="сохранить отчёт в JSON («-» — в stdout)")

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
    # 04.11: инструмент отчёт поддерживал, а оркестратор флаг не проводил
    p6.add_argument("--out", help="отчёт в .md")

    p7 = sub.add_parser("restore", help="обзор/восстановление из бэкапов")
    p7.add_argument("--input", required=True)
    p7.add_argument("--restore", action="store_true")
    p7.add_argument("--file", help="только этот файл (по имени)")

    p8 = sub.add_parser("stats", help="статистика текстов (объём, диалоги, паразиты)")
    p8.add_argument("--input", help="папка или файл (не нужен с --history)")
    p8.add_argument("--limit", type=int)
    p8.add_argument("--out")
    p8.add_argument("--csv", action="store_true",
                    help="дописать строку в reports/stats_log.csv (дневник объёма)")
    # 05.11 (BACKLOG №3): динамика объёма из уже копящегося дневника
    p8.add_argument("--history", action="store_true",
                    help="динамика объёма: слова по датам, дельты, темп")

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
                       ("broken-links", "вики- и markdown-ссылки на несуществующие заметки"),
                       ("merge-finder", "дубликаты по содержимому и по именам"),
                       ("integrity", "целостность .md: пустые, битый UTF-8, frontmatter, заголовки")):
        p = sub.add_parser(name, help=desc)
        p.add_argument("--input", required=True)
        p.add_argument("--limit", type=int)
        p.add_argument("--verbose", action="store_true")
        p.add_argument("--out")
        p.add_argument("--json", dest="json_out",
                       help="сохранить отчёт в JSON («-» — в stdout)")

    p_int = sub.add_parser("obsidian-check",
                           help="валидатор метафайлов Obsidian: таблицы, заголовки, теги, frontmatter")
    p_int.add_argument("--input", required=True)
    p_int.add_argument("--limit", type=int)
    p_int.add_argument("--fix", action="store_true", help="править однозначное (с .bak)")
    p_int.add_argument("--no-bak", action="store_true",
                       help="не делать .bak (для папок под git)")
    p_int.add_argument("--exit-zero", action="store_true",
                       help="код 0, даже если найдены ERROR (для GUI)")
    p_int.add_argument("--verbose", action="store_true")
    p_int.add_argument("--out")
    p_int.add_argument("--json", dest="json_out",
                       help="сохранить отчёт в JSON («-» — в stdout)")

    # 24.10: find_cjk из корня проекта — поиск иероглифов и мойбейка
    p_cjk = sub.add_parser("cjk",
                           help="иероглифы (CJK), мойбейк и порча кодировки (только чтение)")
    p_cjk.add_argument("--input", required=True, help="папка или файл")
    p_cjk.add_argument("--ext", default="",
                       help="расширения через запятую, например .md,.txt")
    p_cjk.add_argument("--json", dest="json_out", default="",
                       help="сохранить полный отчёт в JSON («-» — в stdout)")
    p_cjk.add_argument("--quiet", action="store_true", help="только итог, без деталей")
    # 04.11: код 1 у cjk — штатные находки; флаг для скриптов и GUI
    p_cjk.add_argument("--exit-zero", action="store_true",
                       help="код 0, даже если найдены иероглифы")

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

    p13 = sub.add_parser("emoji-icons",
                         help="эмодзи-иконки → SVG в HTML (с .bak)")
    p13.add_argument("--input", required=True)
    p13.add_argument("--fix", action="store_true",
                     help="заменить (по умолчанию только отчёт)")
    p13.add_argument("--ext", default="html,htm",
                     help="расширения через запятую (по умолчанию html,htm)")
    p13.add_argument("--no-bak", action="store_true",
                     help="не делать .bak-копию (для папок под git)")
    p13.add_argument("--no-markers", action="store_true",
                     help="не переводить служебные textContent-присвоения "
                          "без эмодзи на innerHTML")
    p13.add_argument("--map", dest="map_file",
                     help="JSON со своими заменами: {\"эмодзи\": HTML}")
    p13.add_argument("--limit", type=int)
    p13.add_argument("--out")

    p14 = sub.add_parser("whitespace",
                         help="чистка пробелов и пустых строк (с .bak)")
    p14.add_argument("--input", required=True)
    p14.add_argument("--fix", action="store_true",
                     help="реально править (по умолчанию dry-run)")
    p14.add_argument("--keep-breaks", action="store_true",
                     help="сохранять markdown-переносы (2 пробела в конце строки)")
    p14.add_argument("--out")

    p15 = sub.add_parser("separators",
                         help="чистка мусорных разделителей (с .bak)")
    p15.add_argument("--input", required=True)
    p15.add_argument("--fix", action="store_true",
                     help="реально править (по умолчанию dry-run)")
    p15.add_argument("--symbols",
                     help="символы-разделители (по умолчанию «*/=~-_+%&@•·—–§»)")
    p15.add_argument("--min-run", type=int, default=3,
                     help="минимальная серия символов (по умолчанию 3)")
    p15.add_argument("--max-blank", type=int, default=1,
                     help="пустых строк на месте разделителя (по умолчанию 1)")
    p15.add_argument("--out")

    p16 = sub.add_parser("phrase-check",
                         help="поиск и чистка фраз-штампов ИИ (с .bak)")
    p16.add_argument("--input", help="папка или файл")
    p16.add_argument("--out", help="отчёт в .md (или «-» — в stdout)")
    p16.add_argument("--custom", help="свой YAML-словарь фраз (список строк)")
    p16.add_argument("--phrase", action="append", default=[],
                     help="своя фраза для поиска (можно несколько раз)")
    p16.add_argument("--limit", type=int)
    p16.add_argument("--add", help="добавить фразу в словарь и выйти")
    p16.add_argument("--clean", action="store_true",
                     help="очистка штампов по словарю замен (с бэкапами)")
    p16.add_argument("--review", action="store_true",
                     help="витрина: каждое вхождение с контекстом")
    p16.add_argument("--clean-map", help="свой YAML-словарь (фраза: замена)")
    p16.add_argument("--dry-run", action="store_true",
                     help="очистка: только показать план")
    p16.add_argument("--yes", action="store_true",
                     help="реальная чистка (без неё — только план)")
    p16.add_argument("--no-backup", action="store_true",
                     help="не делать бэкапы при чистке")
    p16.add_argument("--json", dest="json_out",
                     help="отчёт поиска в JSON («-» — в stdout)")

    # 05.11: ё/е-аудит был в GUI и прямым вызовом tools/yo_audit.py,
    # а в textools.py подкоманды не было — по --help команду не найти
    p_yo = sub.add_parser("yo", help="ё/е-аудит: словарные пары, "
                                     "омографы, имена из реестра")
    p_yo.add_argument("--input", required=True,
                      help="папка или файл .md/.txt/.docx")
    p_yo.add_argument("--registry", help="реестр персонажей (yaml)")
    p_yo.add_argument("--dict", dest="dict_", help="свой словарь пар (yaml)")
    p_yo.add_argument("--review", action="store_true",
                      help="печатать каждое вхождение (YO-строки)")
    p_yo.add_argument("--limit", type=int)
    p_yo.add_argument("--out", help="отчёт в .md")

    # 05.11 (BACKLOG №4): экспорт главы Obsidian в Word для беты
    p_exp = sub.add_parser("export-docx",
                           help="глава .md → Word .docx (для беты)")
    p_exp.add_argument("--input", required=True, help=".md файл или папка")
    p_exp.add_argument("--out", required=True,
                       help=".docx файл или папка результата")
    p_exp.add_argument("--force", action="store_true",
                       help="перезаписывать существующие .docx")
    p_exp.add_argument("--limit", type=int)

    p17 = sub.add_parser("check-all",
                         help="профиль «проверить всё»: obsidian-check, cjk, "
                              "integrity, merge-finder, штампы и "
                              "АНТИРЕШИМОСТЬ (скан) одним прогоном")
    p17.add_argument("--input", required=True)
    p17.add_argument("--limit", type=int)
    p17.add_argument("--exit-zero", action="store_true",
                     help="код 0, даже если есть серьёзные находки (для GUI)")
    p17.add_argument("--json", dest="json_out",
                     help="сводка всех проверок в JSON («-» — в stdout)")
    p17.add_argument("--out",
                     help="человекочитаемая md-сводка в файл (журнал)")
    # 05.11 (BACKLOG №2): репетиция чистки — единый план до правок
    p17.add_argument("--plan",
                     help="план правок штампов и АНТИРЕШИМОСТИ в .md "
                          "(ничего не правится)")

    p18 = sub.add_parser("antiresolve", aliases=["pathos"],
                         help="АНТИРЕШИМОСТЬ: поиск, лог и зачистка "
                              "запрещённой лексики и пафоса (памятка романа)")
    p18.add_argument("--input", required=True, help="папка или файл")
    p18.add_argument("--resolve-db",
                     help="словарь лексики (по умолчанию data/resolve_db.yaml)")
    p18.add_argument("--pathos-db",
                     help="словарь антипафоса (по умолчанию data/pathos_db.yaml)")
    p18.add_argument("--clean", action="store_true",
                     help="зачистка: вырезать hard-вхождения (с .bak)")
    p18.add_argument("--log",
                     help="файл лога (по умолчанию reports/antiresolve.log)")
    p18.add_argument("--out", help="отчёт .md («-» — в stdout)")
    p18.add_argument("--json", dest="json_out", nargs="?", const="-",
                     help="сводка в JSON («-» — в stdout)")

    args = ap.parse_args()

    here = Path(__file__).parent
    simple = {"orphan-finder": "orphan_finder",
              "broken-links": "broken_links",
              "merge-finder": "merge_finder",
              "integrity": "integrity_check"}
    if args.cmd in simple:
        sys.path.insert(0, str(here))
        mod = __import__(f"tools.{simple[args.cmd]}", fromlist=["run"])
        opts = ["--input", args.input,
                *(["--limit", str(args.limit)] if args.limit is not None else []),
                *(["--verbose"] if args.verbose else []),
                *(["--out", args.out] if args.out else []),
                *(["--json", args.json_out] if args.json_out else [])]
        sys.exit(mod.main(opts))
    if args.cmd == "obsidian-check":
        sys.path.insert(0, str(here))
        from tools import obsidian_check
        opts = ["--input", args.input,
                *(["--limit", str(args.limit)] if args.limit is not None else []),
                *(["--fix"] if args.fix else []),
                *(["--no-bak"] if args.no_bak else []),
                *(["--exit-zero"] if args.exit_zero else []),
                *(["--verbose"] if args.verbose else []),
                *(["--out", args.out] if args.out else []),
                *(["--json", args.json_out] if args.json_out else [])]
        sys.exit(obsidian_check.main(opts))
    if args.cmd == "cjk":
        sys.path.insert(0, str(here))
        from find_cjk import main as cjk_main
        opts = [args.input,
                *(["--ext", args.ext] if args.ext else []),
                *(["--json", args.json_out] if args.json_out else []),
                *(["--quiet"] if args.quiet else []),
                # 04.11: код 1 — штатные находки; флаг для скриптов
                *(["--exit-zero"] if args.exit_zero else [])]
        sys.exit(cjk_main(opts))
    # 04.11: коды выхода инструментов больше не теряются — раньше
    # sys.exit стоял только у части веток, и consistency/matrix/typography
    # и др. возвращали 0 даже при найденных проблемах.
    if args.cmd == "merge-registry":
        sys.path.insert(0, str(here))
        from tools import registry_merge
        sys.exit(registry_merge.main(
            ["--candidates", args.candidates, "--registry", args.registry,
             *(["--names", args.names] if args.names else []),
             *(["--add"] if args.add else []),
             *(["--out", args.out] if args.out else [])]))
    elif args.cmd == "archive-backups":
        sys.path.insert(0, str(here))
        from tools import backup_archive
        sys.exit(backup_archive.main(
            ["--input", args.input, "--days", str(args.days),
             *(["--move"] if args.move else [])]))
    elif args.cmd == "moc":
        sys.path.insert(0, str(here))
        from tools import moc_builder
        sys.exit(moc_builder.main(
            ["--input", args.input, "--registry", args.registry,
             "--out-dir", args.out_dir,
             *(["--limit", str(args.limit)] if args.limit is not None else []),
             *(["--apply"] if args.apply else []),
             *(["--update"] if args.update else [])]))
    elif args.cmd == "stats":
        sys.path.insert(0, str(here))
        from tools import text_stats
        if args.history:
            # --history: дневник читается, тексты не сканируются
            opts = ["--history",
                    *(["--out", args.out] if args.out else [])]
        else:
            if not args.input:
                print("Ошибка: stats требует --input (или --history)",
                      file=sys.stderr)
                sys.exit(2)
            opts = ["--input", args.input,
                    *(["--limit", str(args.limit)] if args.limit is not None else []),
                    *(["--out", args.out] if args.out else []),
                    *(["--csv"] if args.csv else [])]
        sys.exit(text_stats.main(opts))
    elif args.cmd == "typography":
        sys.path.insert(0, str(here))
        from tools import typography
        sys.exit(typography.main(
            ["--input", args.input, *(["--fix"] if args.fix else []),
             *(["--nbsp"] if args.nbsp else []),
             *(["--out", args.out] if args.out else [])]))
    elif args.cmd == "style-report":
        sys.path.insert(0, str(here))
        from tools import style_report
        sys.exit(style_report.main(
            ["--input", args.input,
             *(["--registry", args.registry] if args.registry else []),
             "--window", str(args.window), "--long", str(args.long),
             *(["--limit", str(args.limit)] if args.limit is not None else []),
             *(["--out", args.out] if args.out else [])]))
    elif args.cmd == "restore":
        sys.path.insert(0, str(here))
        from tools import backup_restore
        sys.exit(backup_restore.main(
            ["--input", args.input, *(["--restore"] if args.restore else []),
             *(["--file", args.file] if args.file else [])]))
    elif args.cmd == "forms":
        sys.path.insert(0, str(here))
        from tools import morph_forms
        sys.exit(morph_forms.main(
            ["--registry", args.registry,
             *(["--fill"] if args.fill else []),
             *(["--out", args.out] if args.out else [])]))
    elif args.cmd == "utf8":
        sys.path.insert(0, str(here))
        from tools import utf8_convert
        sys.exit(utf8_convert.main(
            ["--input", args.input, *(["--fix"] if args.fix else []),
             *(["--limit", str(args.limit)] if args.limit is not None else []),
             *(["--json", args.json_out] if args.json_out else [])]))
    elif args.cmd == "matrix":
        sys.path.insert(0, str(here))
        from tools import character_matrix
        sys.exit(character_matrix.main(
            ["--input", args.input, "--registry", args.registry,
             *(["--limit", str(args.limit)] if args.limit is not None else []),
             *(["--verbose"] if args.verbose else []),
             *(["--out", args.out] if args.out else [])]))
    elif args.cmd == "registry-builder":
        sys.path.insert(0, str(here))
        from tools import registry_builder
        sys.exit(registry_builder.main(
            ["--input", args.input, *(["--out", args.out] if args.out else []),
             *(["--registry", args.registry] if args.registry else []),
             "--min-count", str(args.min_count),
             *(["--limit", str(args.limit)] if args.limit is not None else []),
             *(["--verbose"] if args.verbose else [])]))
    elif args.cmd == "consistency":
        sys.path.insert(0, str(here))
        from tools import consistency
        sys.exit(consistency.main(
            ["--input", args.input, "--registry", args.registry,
             *(["--limit", str(args.limit)] if args.limit is not None else []),
             *(["--verbose"] if args.verbose else []),
             *(["--out", args.out] if args.out else [])]))
    elif args.cmd == "emoji-icons":
        sys.path.insert(0, str(here))
        from tools import icon_replace
        sys.exit(icon_replace.main(
            ["--input", args.input,
             *(["--fix"] if args.fix else []),
             *(["--ext", args.ext] if args.ext else []),
             *(["--no-bak"] if args.no_bak else []),
             *(["--no-markers"] if args.no_markers else []),
             *(["--map", args.map_file] if args.map_file else []),
             *(["--limit", str(args.limit)] if args.limit is not None else []),
             *(["--out", args.out] if args.out else [])]))
    elif args.cmd == "whitespace":
        sys.path.insert(0, str(here))
        from tools import whitespace_clean
        sys.exit(whitespace_clean.main(
            ["--input", args.input,
             *(["--fix"] if args.fix else []),
             *(["--keep-breaks"] if args.keep_breaks else []),
             *(["--out", args.out] if args.out else [])]))
    elif args.cmd == "separators":
        sys.path.insert(0, str(here))
        from tools import separator_clean
        sys.exit(separator_clean.main(
            ["--input", args.input,
             *(["--fix"] if args.fix else []),
             *(["--symbols", args.symbols] if args.symbols else []),
             "--min-run", str(args.min_run),
             "--max-blank", str(args.max_blank),
             *(["--out", args.out] if args.out else [])]))
    elif args.cmd == "phrase-check":
        sys.path.insert(0, str(here))
        from tools import phrase_check
        opts = []
        if args.input:
            opts += ["--input", args.input]
        if args.out:
            opts += ["--out", args.out]
        if args.custom:
            opts += ["--custom", args.custom]
        for ph in args.phrase:
            opts += ["--phrase", ph]
        if args.limit is not None:
            opts += ["--limit", str(args.limit)]
        if args.add:
            opts += ["--add", args.add]
        if args.clean:
            opts.append("--clean")
        if args.review:
            opts.append("--review")
        if args.clean_map:
            opts += ["--clean-map", args.clean_map]
        if args.dry_run:
            opts.append("--dry-run")
        if args.yes:
            opts.append("--yes")
        if args.no_backup:
            opts.append("--no-backup")
        if args.json_out:
            opts += ["--json", args.json_out]
        sys.exit(phrase_check.main(opts))
    elif args.cmd == "yo":
        sys.path.insert(0, str(here))
        from tools import yo_audit
        opts = ["--input", args.input,
                *(["--registry", args.registry] if args.registry else []),
                *(["--dict", args.dict_] if args.dict_ else []),
                *(["--review"] if args.review else []),
                *(["--limit", str(args.limit)] if args.limit is not None else []),
                *(["--out", args.out] if args.out else [])]
        sys.exit(yo_audit.main(opts))
    elif args.cmd == "export-docx":
        sys.path.insert(0, str(here))
        from tools import export_docx
        sys.exit(export_docx.main(
            ["--input", args.input, "--out", args.out,
             *(["--force"] if args.force else []),
             *(["--limit", str(args.limit)] if args.limit is not None else [])]))
    elif args.cmd == "check-all":
        sys.path.insert(0, str(here))
        from tools import full_check
        sys.exit(full_check.main(
            ["--input", args.input,
             *( ["--limit", str(args.limit)] if args.limit is not None else []),
             *( ["--exit-zero"] if args.exit_zero else []),
             *( ["--json", args.json_out] if args.json_out else []),
             *( ["--out", args.out] if args.out else []),
             *( ["--plan", args.plan] if args.plan else [])]))
    elif args.cmd in ("antiresolve", "pathos"):
        sys.path.insert(0, str(here))
        from tools import antiresolve
        opts = ["--input", args.input]
        if args.resolve_db:
            opts += ["--resolve-db", args.resolve_db]
        if args.pathos_db:
            opts += ["--pathos-db", args.pathos_db]
        if args.clean:
            opts.append("--clean")
        if args.log:
            opts += ["--log", args.log]
        if args.out:
            opts += ["--out", args.out]
        if args.json_out:
            opts += ["--json", args.json_out]
        sys.exit(antiresolve.main(opts))


if __name__ == "__main__":
    # 05.11: пустой/несуществующий --input — понятное сообщение и код 2
    # вместо трейсбека (ValueError поднимают проверщики пути в core)
    try:
        main()
    except ValueError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(2)
