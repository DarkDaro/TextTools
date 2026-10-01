# TextTools

Настольный набор инструментов для анализа и массовой обработки текстовых
заметок (markdown-хранилища Obsidian, txt, docx): реестр персонажей
с морфологией, проверка консистентности имён, матрица упоминаний,
поиск «осиротевших» заметок, битых ссылок и дубликатов, чистка штампов,
пробелов и эмодзи, массовые замены, обслуживание кодировок и бэкапов.

**Полное руководство пользователя (для авторов и писателей) —
[MANUAL.md](MANUAL.md): готовые сценарии, справочник по всем кнопкам и
полям, формат реестра, частые вопросы.**

Два режима запуска:

* **CLI** — `textools.py` (единая точка входа, argparse-подкоманды)
* **GUI** — `gui_ctk.pyw` на CustomTkinter (5 вкладок), запуск через
  `textools_gui.bat` или `python gui_ctk.pyw`

## Установка

```
pip install -r requirements.txt
```

Зависимости: `pyyaml`, `python-docx`, `customtkinter`, `pymorphy3`
(падежные формы имён), `charset-normalizer` (определение кодировок).

## Возможности

* **Персонажи**: registry-builder находит имена-кандидаты; реестр YAML
  (`имя/формы/старое/старое_опасное/опечатки`); consistency проверяет
  тексты по реестру, находя старые имена и опечатки в любых падежах
  (pymorphy3, ё/е эквивалентны); forms дописывает недостающие падежи
  в реестр; matrix строит таблицу «персонаж × файл».
* **Хранилище**: orphan-finder, broken-links, merge-finder, поиск и
  интерактивная чистка штампов (витрина с выбором вхождений).
* **Замены**: массовая замена в .md/.txt/.docx (в docx — включая фразы,
  разорванные между run'ами, с сохранением форматирования), диагностика
  символов и кодировок, точечная замена слова, regex-замена по папке.
* **Чистка**: эмодзи и смайлы, мусор/CJK по белому списку, пробелы и
  пустые строки вне код-блоков, приведение текстов к UTF-8 (koi8-r,
  cp1251 распознаются автоматически).
* **Обслуживание**: обзор и восстановление из бэкапов (`.bak` и
  `md_replace_backups/`), архивация старых бэкапов в `archive/backups`
  (перенос, ничего не удаляется), история операций в `logs/history.log`,
  мягкая остановка долгих операций (кнопка «Стоп» даёт программе
  корректно завершить текущий файл).

## CLI

```
python textools.py registry-builder --input <папка> [--registry <yaml>] [--min-count N]
python textools.py consistency      --input <папка> --registry <yaml>
python textools.py forms            --registry <yaml> [--fill]
python textools.py matrix           --input <папка> --registry <yaml>
python textools.py merge-registry   --candidates <yaml> --registry <yaml> [--add]
python textools.py utf8             --input <папка> [--fix]
python textools.py orphan-finder    --input <папка>
python textools.py broken-links     --input <папка>
python textools.py merge-finder     --input <папка>
python textools.py restore          --input <папка> [--restore] [--file <имя>]
python textools.py archive-backups  --input <папка> [--days 30] [--move]
python textools.py moc              --input <vault> --registry <yaml> --out-dir <папка> [--apply]
python textools.py stats            --input <папка> [--out report.md]
```

Общие опции: `--out <файл>` (отчёт), `--limit N`, `--verbose`.
Долгие операции печатают прогресс `PROGRESS:N/M`.

## GUI

Вкладки:

* **Имена персонажей** — registry-builder, consistency, матрица
  упоминаний, падежные формы (pymorphy3), добавление кандидатов в
  реестр, MOC-заметки персонажей для Obsidian
* **Хранилище** — orphan-finder, broken-links, merge-finder, поиск
  штампов, чистка штампов (в том числе интерактивно, с витриной)
* **Чистка** — эмодзи, мусор/CJK, пробелы, кодировки (UTF-8)
* **Замены** — md_replace (4 режима), char_search, точечная замена
  слова, refile
* **Настройки** — пути к внешним скриптам, тема, обслуживание бэкапов,
  общие параметры

У каждого поля и кнопки есть всплывающая подсказка. Долгие операции
показывают прогресс-бар.

**Безопасность:** все операции с записью идут в dry-run; реальная запись
только через чекбокс «Применить изменения». Перед записью создаются
бэкапы (`.bak` рядом или `md_replace_backups/<дата-время>/`;
восстановление — вкладка «Настройки»).

Конфиг GUI — `gui_config.json` (пути, тема, состояния чекбоксов).

## Структура

* `core/` — парсер текста, реестр имён, сканер vault, docx (включая
  кросс-run замену), морфология (pymorphy3), кодировки
* `tools/` — движки команд (registry_builder, consistency, orphan_finder,
  broken_links, merge_finder, phrase_check, whitespace_clean,
  utf8_convert, morph_forms, character_matrix, registry_merge,
  backup_restore, backup_archive, moc_builder, text_stats) + словари
  `phrases*.yaml`
* `wrappers/` — сборка командных строк для **внешних** скриптов
  (emoji-cleaner, md-replace, char_search, refile, clean_text_files);
  сами скрипты лежат вне репозитория, пути задаются в
  `wrappers/__init__.py::DEFAULTS` и переопределяются в настройках GUI
* `gui_ctk.pyw`, `tabs_*.py`, `widgets_ctk.py`, `review_dialog.py` — GUI
* `synthetic/` — синтетические тестовые данные
* `reports/` — выходные отчёты (в git не входит)

## Тесты

Тесты лежат в `archive/` (не входит в git):

```
cd archive
python test_engines.py   # проверки движков и CLI
python test_gui.py       # проверки GUI (открывает окно приложения)
```

Каждый набор сам пересоздаёт тестовый корпус `archive/corpus/`, порядок
запуска не важен. Подробности — `archive/README.md`.
