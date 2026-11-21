# Соответствие CLI ↔ GUI

Зачем: программа должна работать одинаково для человека, который
тыкает кнопки, и для терминала. Различия допустимы только там, где
у канала другая природа (журнал вместо файла, витрина вместо
флага `--yes`) — и каждое из них описано здесь.

## Принцип

* CLI-подкоманда зовёт `tools/<движок>.main(argv)`.
* Кнопка GUI зовёт тот же движок той же функцией: `run_internal`
  передаёт те же строковые аргументы (`--input`, `--fix`, `--registry`…),
  что и терминал. Отдельных «GUI-версий логики» нет.
* Витрины (штампы, ё/е) — тот же движок, но выбор вхождений через
  диалог; у CLI та же работа делается флагами `--clean --yes`
  (штампы) и `--review` (ё/е).
* Долгие операции печатают `PROGRESS:N/M` — движок один, полоса
  прогресса GUI рисует по тем же строкам.

Правило при новых функциях: добавили ключ CLI — либо повторить его
в GUI, либо дописать строку «почему нет» в таблицу ниже. Добавили
кнопку GUI — движок должен существовать, его CLI-ключи повторяются
в карточке или обоснованно опускаются.

## Имена персонажей

| Карточка GUI | Движок | CLI | Ключи GUI | Ключи только CLI |
|---|---|---|---|---|
| Найти кандидатов | registry_builder | registry-builder | --input, --min-count, --out, --registry | --limit, --verbose (прогон по расписанию) |
| Проверить имена | consistency | consistency | --input, --registry | — |
| Построить матрицу | character_matrix | matrix | --input, --registry | --limit, --verbose |
| Показать недостающие падежи | morph_forms | forms | --registry, --fill | — |
| Добавить кандидатов в реестр | registry_merge | merge-registry | --candidates, --registry, --names, --add | — |
| MOC-заметки персонажей | moc_builder | moc | --input, --registry, --out-dir, --apply, --update (18.11) | --limit |
| Список персонажей | cast_list | cast | --input | --out, --min-count |
| Проверка названия | name_check | name-check | --name | --out |

## Писателям

| Карточка GUI | Движок | CLI | Ключи GUI | Ключи только CLI |
|---|---|---|---|---|
| АНТИРЕШИМОСТЬ | antiresolve | antiresolve (pathos) | --input, --clean | --log, --out, --json (журнал вместо файла) |
| Найти штампы / Почистить штампы | phrase_check | phrase-check | --input; чистка — витрина выбора | --clean --yes (пакет без витрины), --out |
| Стилистический отчёт | style_report | style-report | --input, --registry, --window, --long | --out |
| Статистика | text_stats | stats | --input, --csv, --history (18.11) | --out, --limit |
| Эхо-фразы | echo_finder | echo | --input, --n, --min-files, --top | --registry, --out |
| Ё/Е-аудит (витрина) | yo_audit | yo | движок в потоке + витрина | --input, --registry, --review, --out (пакетный прогон) |
| Типографика / Вычитка | typography | typography | --input, --fix, --nbsp; --check | — |
| Экспорт в Word | export_docx | export-docx | --input, --out, --force | — |

## Хранилище

| Карточка GUI | Движок | CLI | Ключи GUI | Ключи только CLI |
|---|---|---|---|---|
| Orphans / Битые ссылки / Дубликаты / Целостность | orphan_finder, broken_links, merge_finder, integrity_check | orphan-finder, broken-links, merge-finder, integrity | --input | --limit, --verbose, --out |
| Проверить заметки | obsidian_check | obsidian-check | --input, --fix, --no-bak, --out | --exit-zero (для скриптов; в GUI код 1 честно показывается как «есть замечания») |
| Найти иероглифы | find_cjk | cjk | --input (--ext берётся из настройки cjk_ext) | --json |
| Проверить всё (6 проверок) | full_check | check-all | --input | --out, --plan, --json (план и машинные сводки — терминальные) |

## Чистка

| Карточка GUI | Движок | CLI | Ключи GUI | Ключи только CLI |
|---|---|---|---|---|
| Чистка пробелов | whitespace_clean | whitespace | --input, --fix, --keep-breaks | — |
| Кодировки | utf8_convert | utf8 | --input, --fix | — |
| Эмодзи-иконки | icon_replace | emoji-icons | --input, --fix, --no-bak | --map (свой icons.json — ниша) |
| Отбойники | separator_clean | separators | --input, --fix, --min-run, --symbols | — |

Внешние скрипты (emoji-cleaner, clean_text, md_replace, char_search,
refile) — только GUI: это личные скрипты автора из `external/`, CLI-подкоманд
им не заводили намеренно. В терминале они вызываются напрямую
(`python external/...`); обёртки `wrappers/` собирают те же командные
строки, что и кнопки.

## Настройки

| Карточка GUI | Движок | CLI | Ключи GUI | Ключи только CLI |
|---|---|---|---|---|
| Показать / восстановить бэкапы | backup_restore | restore | --input, --file, --restore | — |
| Показать старые бэкапы / Архивировать | backup_archive | archive-backups | --input, --days, --move | — |
| Найти старые копии и ярлыки | copy_doctor | copy-doctor | без ключей (dry-run) | --fix, --roots |
| Создать свежий ярлык | copy_doctor | copy-doctor --new-shortcut | то же | — |
| Полная проверка (doctor) | app_check | doctor | без ключей (18.11) | --json |
| Проверка целостности | app_check | doctor | без ключей (21.11) | --json |
| Проверить обновления | updater | update (по умолчанию) | --check | — |
| Обновить сейчас | updater | update --apply | --apply | — |

## Помодоро

Вкладка появилась 18.11.2026 как бонус-фича и CLI-команды не имеет:

| Карточка GUI | Движок | CLI | Ключи GUI | Ключи только CLI |
|---|---|---|---|---|
| Старт/Пауза, Сброс, Пропустить фазу | core/pomodoro.py (PomodoroEngine) | нет | — | — |
| Длительности и автостарт (18.11: раздел «Помодоро» на «Настройках») | core/pomodoro.py + конфиг | нет | pomo.work_min, pomo.short_min, pomo.long_min, pomo.rounds, pomo.auto_break, pomo.auto_work, pomo.sound | — |
| Сегодня (счётчики дня) | core/pomodoro.py (ensure_day) | нет | pomo.stats | — |

Почему нет CLI: интерактивный таймер — живой интерфейс (обратный
отсчёт на экране, пауза, подсказка в конце фазы); терминалу рисовать
некуда. Логика фаз при этом вынесена в core/pomodoro.py — чистый
модуль без tkinter, покрытый test/test_pomodoro.py; если CLI-режим
понадобится (python textools.py pomodoro --work 25), он переиспользует
тот же движок.

## Что осознанно только у одного канала

**Только CLI:** `--json` (машинно-читаемые отчёты), `--out` (файл
вместо журнала), `--limit`/`--verbose` (расписания и скрипты),
`--exit-zero` (код выхода для CI), `--map`. Это терминальные
сценарии: окно для них не нужно. С 18.11.2026 (1.8.5) к этому ряду —
`--lang ru|en` у шести языковых команд (registry-builder, cast,
style-report, stats, echo, antiresolve): в GUI язык текстов и язык
интерфейса задаются разделом «Язык» на «Настройках» и читаются
инструментами из gui_config.json, флаг нужен терминалу для
разового переопределения.

**Только GUI:** витрины выбора вхождений (штампы, ё/е), внешние
скрипты, история путей с правым кликом, drag&drop, тосты и
прогресс, интерактивный помодоро-таймер (18.11: живой интерфейс,
движок общий — core/pomodoro.py). Решение принимает человек —
терминал ему не конкурент.

## Статус аудита

Аудит проведён 18.11.2026: все 31 подкоманда CLI сопоставлены с
карточками GUI, дефолты сверены (min-count 2/2, days 30/30,
--exit-zero сознательно скрыт). Закрытые расхождения:
`moc --update`, `stats --history`, `doctor` — в GUI добавлены
(18.11.2026). Повторный проход 18.11.2026 при переносе настроек
таймера на «Настройки»: ключи те же, правка доезжает в таймер
мгновенно, расхождений нет. Следующий аудит — при следующем большом
добавлении функций.
