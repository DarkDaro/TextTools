# archive — тесты textools

Синтетические тесты всего функционала: каждый движок, каждая опция CLI,
каждая кнопка и опция GUI. Ничего не удаляют; реальные записи идут только
внутрь `corpus/` (регенерируется с нуля при каждом запуске).

## Состав

- `gen_corpus.py` — генератор тестового корпуса `corpus/`: имена + реестр,
  vault со ссылками/orphan/дубликатами, штампы ИИ, пробелы/табы/код-блоки,
  docx (имена, разорванные run'ы, эмодзи, пустые параграфы), кодировки
  (koi8/cp1251/бинарь/пустой), файлы для refile/emoji/CJK.
- `test_engines.py` — 95 проверок движков и CLI: core (text_parser,
  name_registry, vault_scanner, docx_io), tools (registry_builder,
  consistency, orphan/broken/merge, phrase_check + clean + dry-run + бэкапы,
  whitespace_clean + keep-breaks + docx), wrappers (все cmd_*), CLI
  textools.py (5 подкоманд) и все внешние скрипты (emoji_cleaner,
  clean_text_files, md_replace: dry/real/find-bad/fix-encoding/strip-bad,
  char_search + --fix-word, refile).
- `test_gui.py` — 43 проверки GUI: структура вкладок, регресс «нет
  невидимых виджетов», все кнопки всех 5 вкладок с сухими и реальными
  режимами, валидация пустых полей, отчёты в reports/, default_vault
  fallback. Не нажимаются тестом: «Открыть конфиг» (блокнот) и
  «Сбросить всё» (удаляет gui_config.json).

## Запуск (из этой папки)

```
python test_engines.py
python test_gui.py
```

Каждый набор сам пересоздаёт корпус — порядок запуска не важен.
GUI-тест открывает окно приложения на время прогона.
