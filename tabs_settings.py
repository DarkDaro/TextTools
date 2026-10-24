"""Вкладка «Настройки»: пути к внешним скриптам, проверки, общие параметры.
18.09: переделана на CustomTkinter (widgets_ctk)."""
import sys

import customtkinter as ctk

from pathlib import Path

from gui_config import CFG, CONFIG_FILE
from widgets_ctk import (PathField, EntryField, CheckField, HelpBox,
                         Section, Tooltip, ActionButton, button_row,
                         FONT_SMALL)
from wrappers import DEFAULTS


class SettingsTab(ctk.CTkFrame):
    LABEL = "Настройки"

    def _build(self, parent):
        HelpBox(parent, text=(
            "Здесь задаются пути к внешним скриптам (в репозиторий они не "
            "входят). Пока путь не указан, соответствующие кнопки сообщат "
            "об этом. Все настройки сохраняются автоматически."))

        s1 = Section(parent, "Пути к внешним скриптам")
        for label, key in (("emoji-cleaner:", "emoji_cleaner"),
                           ("clean_text_files:", "clean_text"),
                           ("md_replace:", "md_replace"),
                           ("char_search:", "char_search"),
                           ("refile:", "refile")):
            default = DEFAULTS[key]
            tip = (f"Путь к скрипту. По умолчанию: {default}" if default else
                   "Путь к скрипту. По умолчанию не задан — укажите вручную.")
            PathField(s1.inner, label, f"script_{key}", CFG, file_mode="file",
                      tooltip=tip)
        ctk.CTkLabel(s1.inner, anchor="w", font=FONT_SMALL,
                     text_color=("gray45", "gray60"),
                     text="Пусто = путь по умолчанию (встроенный или не задан)."
                     ).pack(anchor="w", pady=(2, 0))
        row1 = button_row(s1.inner)
        ActionButton(row1, "Проверить пути", self._check_scripts,
                     kind="safe", width=200,
                     tooltip="Проверить все пути: настроен ли скрипт и "
                             "существует ли файл.").pack(side="left")

        s2 = Section(parent, "Общее")
        self.f_default_vault = PathField(
            s2.inner, "Vault по умолчанию:", "default_vault", CFG, file_mode="dir",
            tooltip="Подставляется в поля хранилища на других вкладках, "
                    "если они пустые.")
        ctk.CTkLabel(s2.inner, anchor="w", font=FONT_SMALL,
                     text_color=("gray45", "gray60"),
                     text="Пусто = поля хранилища остаются пустыми."
                     ).pack(anchor="w", pady=(0, 2))
        CheckField(s2.inner, "Показывать команды в логе", "show_cmd", CFG, default=True,
                   tooltip="Показывать в окне вывода командную строку перед результатом."
                   ).pack(anchor="w")
        CheckField(s2.inner, "Переходить в журнал при запуске", "jump_log",
                   CFG, default=True,
                   tooltip="После нажатия кнопки инструмента открывается "
                           "вкладка «Журнал» с ходом работы. Без галочки "
                           "остаётесь на текущей вкладке."
                   ).pack(anchor="w")
        CheckField(s2.inner, "Звуковые сигналы", "sound", CFG, default=True,
                   tooltip="Короткие системные звуки: ошибка операции, "
                           "«Уже запущено», завершение. С ошибкой звук "
                           "всегда заметный."
                   ).pack(anchor="w")
        CheckField(s2.inner, "Тост при завершении", "toast_done", CFG, default=True,
                   tooltip="Всплывающее сообщение «Готово: инструмент» "
                           "справа снизу экрана. Ошибки и предупреждения "
                           "показываются независимо от этой галочки."
                   ).pack(anchor="w")

        # --- Проверки заметок (24.10) ---
        s_checks = Section(parent, "Проверки заметок")
        self.f_cjk_ext = EntryField(
            s_checks.inner, "Расширения для иероглифов:", "cjk_ext", CFG,
            width_label=230, placeholder=".md,.txt",
            tooltip="Список расширений для поиска иероглифов через запятую. "
                    "Пусто = стандартный набор: .md, .txt, .json, .yaml "
                    "и другие текстовые файлы.")
        self.f_cjk_ext.pack(fill="x")
        CheckField(
            s_checks.inner, "Валидатор Obsidian: не создавать .bak",
            "obs_no_bak", CFG, default=False,
            tooltip="Для папок под git: историю хранит сам git, копии "
                    ".bak рядом с заметками не нужны. Внимание: без "
                    "бэкапа откатить правку будет нечем."
            ).pack(anchor="w")
        ctk.CTkLabel(
            s_checks.inner, justify="left", anchor="w", font=FONT_SMALL,
            text_color=("gray45", "gray60"),
            text="Расширения и поведение .bak применяются к карточкам "
                 "«Валидатор заметок Obsidian» и «Иероглифы и порча "
                 "кодировки» на вкладке «Хранилище»."
            ).pack(anchor="w", pady=(0, 2))

        # --- Вид и журнал (24.10) ---
        s_view = Section(parent, "Вид и журнал")
        self.f_report_dir = PathField(
            s_view.inner, "Папка отчётов:", "report_dir", CFG,
            file_mode="dir",
            tooltip="Куда предлагать сохранение отчётов из журнала. "
                    "Пусто = reports/ рядом с программой.")
        ctk.CTkLabel(s_view.inner, anchor="w", font=FONT_SMALL,
                     text_color=("gray45", "gray60"),
                     text="Пусто = reports/ рядом с программой."
                     ).pack(anchor="w", pady=(0, 2))
        self.f_log_limit = EntryField(
            s_view.inner, "Строк в журнале:", "ui.log_limit", CFG,
            width_label=170, placeholder="5000",
            tooltip="Сколько последних строк хранить в окне журнала. "
                    "Старые строки сверх лимита убираются только из окна, "
                    "файлы не затрагиваются. По умолчанию 5000.")
        self.f_log_limit.pack(fill="x")
        CheckField(
            s_view.inner, "Спрашивать при закрытии во время работы",
            "confirm_close", CFG, default=True,
            tooltip="Если нажать крестик, пока инструмент ещё пишет файлы, "
                    "программа спросит подтверждение и предложит мягкую "
                    "остановку. Без галочки окно закрывается сразу."
            ).pack(anchor="w")
        CheckField(
            s_view.inner, "Запоминать размер окна", "remember_geometry",
            CFG, default=True,
            tooltip="Сохранять ширину, высоту и положение окна между "
                    "запусками. Если окно уехало за край, снимите галочку "
                    "или нажмите «Сбросить размер окна»."
            ).pack(anchor="w")
        CheckField(
            s_view.inner, "Открывать последнюю вкладку", "remember_tab",
            CFG, default=True,
            tooltip="При запуске возвращаться на тот раздел, где вы "
                    "закончили. Без галочки всегда открывается первая "
                    "вкладка."
            ).pack(anchor="w")
        row_view = button_row(s_view.inner)
        ActionButton(row_view, "Сбросить размер окна", self._reset_geometry,
                     kind="neutral", width=230,
                     tooltip="Вернуть окно к рабочему размеру по центру "
                             "экрана, если оно уехало за край или стало "
                             "слишком маленьким.").pack(side="left")

        # 24.10: мягкая проверка полей — при уходе фокуса, без блокировки ввода
        self.f_default_vault.entry.bind("<FocusOut>", self._check_vault, add="+")
        self.f_report_dir.entry.bind("<FocusOut>", self._check_report_dir, add="+")
        self.f_log_limit.entry.bind("<FocusOut>", self._check_log_limit, add="+")
        self.f_cjk_ext.entry.bind("<FocusOut>", self._check_cjk_ext, add="+")

        # --- Сохранение / сброс ---
        s3 = Section(parent, "Сохранение настроек")
        ctk.CTkLabel(s3.inner, justify="left", anchor="w", font=FONT_SMALL, text=(
            "Все настройки сохраняются автоматически при каждом изменении "
            "(путь, галочка, тема). Кнопки ниже — для ручного управления."
        )).pack(anchor="w", pady=(0, 4))
        r3 = button_row(s3.inner, pady=(2, 0))
        ActionButton(r3, "Сохранить сейчас", self._save_now,
                     kind="primary", width=190,
                     tooltip="Принудительно записать все текущие значения "
                             "в gui_config.json.").pack(side="left", padx=(0, 8))
        b_open = ActionButton(r3, text="Открыть конфиг", command=self._open_config,
                              kind="neutral", width=160)
        b_open.pack(side="left", padx=(0, 8))
        Tooltip(b_open, "Открыть файл настроек в Блокноте. "
                        "Можно править вручную; изменения подхватятся после перезапуска.")
        b_reset = ActionButton(r3, "Сбросить всё", self._reset_all,
                               kind="danger", width=160)
        b_reset.pack(side="left")
        Tooltip(b_reset, "Очистить все сохранённые настройки (пути, галочки, тема). "
                         "Действие спрашивает подтверждение; после сброса "
                         "перезапустите программу.")

        # --- Обслуживание бэкапов (01.10) ---
        s_bak = Section(parent, "Обслуживание бэкапов (.bak и md_replace_backups)")
        self.f_bak_dir = PathField(s_bak.inner, "Папка хранилища:", "bak_dir", CFG,
                                   file_mode="both",
                                   tooltip="Папка, в которой искать .bak рядом с "
                                           "файлами и снимки md_replace_backups.")
        self.f_bak_file = EntryField(s_bak.inner, "Файл (необязательно):", "bak_file",
                                     CFG, placeholder="все",
                                     tooltip="Восстановить только один файл по имени. "
                                             "Пусто = все найденные.")
        self.c_bak_restore = CheckField(s_bak.inner, "Восстановить",
                                        "bak_restore", CFG, default=False,
                                        tooltip="Без галочки — только обзор. "
                                                "С галочкой — вернуть прежнее "
                                                "содержимое (текущее сохраняется "
                                                "как .pre-restore.bak).")
        self.c_bak_restore.pack(anchor="w")
        row_bak = button_row(s_bak.inner)
        b_bak = ActionButton(
            row_bak, "Показать / восстановить бэкапы", self._run_backup,
            kind="safe", width=300,
            tooltip="Обзор всех бэкапов; с галочкой «Восстановить» — "
                    "откат к прежнему содержимому.")
        b_bak.pack(side="left")
        b_bak.link_danger(self.c_bak_restore.var)
        self.f_bak_days = EntryField(s_bak.inner, "Старше (дней):", "bak_days", CFG,
                                     placeholder="30",
                                     tooltip="Архивируются бэкапы старше этого "
                                             "числа дней.")
        self.c_bak_move = CheckField(s_bak.inner, "Архивировать (перенести)",
                                     "bak_move", CFG, default=False,
                                     tooltip="Без галочки — только обзор. "
                                             "С галочкой — переносит старые бэкапы "
                                             "в archive/backups (НИЧЕГО не удаляется, "
                                             "структура сохраняется).")
        self.c_bak_move.pack(anchor="w")
        row_bak2 = button_row(s_bak.inner)
        b_arch = ActionButton(
            row_bak2, "Показать старые бэкапы / Архивировать", self._run_archive,
            kind="safe", width=320,
            tooltip="Бэкапы старше N дней переносятся в централизованный "
                    "архив textools — с сохранением структуры и без "
                    "перезаписи.")
        b_arch.pack(side="left")
        b_arch.link_danger(self.c_bak_move.var)

        # --- Журнал операций (02.10) ---
        s_h = Section(parent, "Журнал операций")
        ctk.CTkLabel(s_h.inner, justify="left", anchor="w", font=FONT_SMALL, text=(
            "Каждый запуск инструмента из GUI пишется в logs/history.log: "
            "время, команда, код завершения и длительность. "
            "Удобно вспомнить, что и когда делалось с текстами."
        )).pack(anchor="w", pady=(0, 4))
        b_hist = ActionButton(s_h.inner, "Открыть журнал", self._open_history,
                              kind="neutral", width=180)
        b_hist.pack(anchor="w")
        Tooltip(b_hist, "Открыть logs/history.log в Блокноте. "
                        "Файл можно удалять целиком — при следующей операции "
                        "он создастся заново.")

        # --- О программе (24.10) ---
        s_about = Section(parent, "О программе")
        ctk.CTkLabel(
            s_about.inner, justify="left", anchor="w", font=FONT_SMALL,
            text=(f"TextTools {self._version()}  •  Python "
                  f"{sys.version.split()[0]}\n"
                  "Лицензия MIT, © 2026 DarkDaro\n"
                  "https://github.com/DarkDaro/TextTools")
            ).pack(anchor="w", pady=(0, 6))
        row_about = button_row(s_about.inner)
        ActionButton(row_about, "Проверить зависимости", self._check_deps,
                     kind="safe", width=220,
                     tooltip="Проверить, установлены ли обязательные пакеты "
                             "и какие у них версии."
                     ).pack(side="left", padx=(0, 8))
        ActionButton(row_about, "Скопировать сведения", self._copy_info,
                     kind="neutral", width=210,
                     tooltip="Скопировать версию, Python, систему и версии "
                             "зависимостей в буфер обмена — удобно приложить "
                             "к сообщению об ошибке."
                     ).pack(side="left", padx=(0, 8))
        ActionButton(row_about, "Открыть README", self._open_readme,
                     kind="neutral", width=170,
                     tooltip="README.md: описание проекта и список "
                             "возможностей.").pack(side="left", padx=(0, 8))
        ActionButton(row_about, "Папка проекта", self._open_project_dir,
                     kind="neutral", width=160,
                     tooltip="Открыть папку, из которой запущена программа."
                     ).pack(side="left")

        s4 = Section(parent, "Информация")
        ctk.CTkLabel(s4.inner, justify="left", anchor="w", font=FONT_SMALL, text=(
            f"Настройки хранятся в: {CONFIG_FILE}\n"
            "Отчёты сохраняются в: reports/ (рядом с программой)\n\n"
            "Безопасность:\n"
            "  • Всё, что меняет файлы, по умолчанию в dry-run (только отчёт)\n"
            "  • Реальная запись — только явный чекбокс «Применить изменения»\n"
            "  • Бэкапы: .bak рядом с файлами или md_replace_backups в хранилище\n"
            "  • Кнопка «Стоп» в статусной строке над вкладками "
            "прерывает запущенную операцию"
        )).pack(anchor="w")
        r4 = button_row(s4.inner, pady=(6, 0))
        b_rep = ActionButton(r4, "Открыть папку отчётов", self._open_reports,
                             kind="neutral", width=210)
        b_rep.pack(side="left", padx=(0, 8))
        Tooltip(b_rep, "Папка отчётов из настроек (по умолчанию reports/). "
                       "Сюда же предлагается сохранять журнал.")
        b_par = ActionButton(r4, "Открыть список паразитов", self._open_parasites,
                             kind="neutral", width=220)
        b_par.pack(side="left")
        Tooltip(b_par, "tools/parasites.yaml — свой список слов-паразитов "
                       "для статистики. При первом открытии создаётся шаблон "
                       "из встроенного списка.")
        # 24.10: инструкция по окну лежит рядом с программой
        b_guide = ActionButton(r4, "Открыть инструкцию", self._open_guide,
                               kind="neutral", width=200)
        b_guide.pack(side="left", padx=8)
        Tooltip(b_guide, "GUI_GUIDE.md: пошаговое руководство по окну "
                         "для пользователей без опыта программирования.")

    def _log(self, msg, tag=None):
        from gui_ctk import _app
        _app.log_line(msg, tag)

    # --- проверки полей (24.10) ---

    def _check_vault(self, _e=None):
        p = self.f_default_vault.get()
        if p and not Path(p).is_dir():
            self._log(f"Vault по умолчанию не найден: {p}\n", "warn")

    def _check_report_dir(self, _e=None):
        p = self.f_report_dir.get()
        if p and not Path(p).is_dir():
            self._log(f"Папки отчётов пока нет: {p} "
                      "(она будет создана при сохранении).\n", "warn")

    def _check_log_limit(self, _e=None):
        v = self.f_log_limit.get().strip()
        if not v:
            return
        if not v.isdigit() or int(v) < 500:
            self.f_log_limit.set("5000")
            self._log("«Строк в журнале»: нужно целое число 500 или больше. "
                      "Возвращено 5000.\n", "warn")
        elif int(v) > 100000:
            self.f_log_limit.set("100000")
            self._log("«Строк в журнале»: больше 100000 держать в окне "
                      "не стоит. Поставлено 100000.\n", "warn")

    def _check_cjk_ext(self, _e=None):
        raw = self.f_cjk_ext.get().strip()
        if not raw:
            return
        parts = []
        for token in raw.replace(";", ",").split(","):
            token = token.strip().lower()
            if not token:
                continue
            if not token.startswith("."):
                token = "." + token
            if any(ch in token for ch in "\\/:*?\"<>| "):
                self._log(f"«Расширения для иероглифов»: пропущено «{token}» — "
                          "это не расширение.\n", "warn")
                continue
            parts.append(token)
        normalized = ",".join(dict.fromkeys(parts))
        if normalized != raw:
            self.f_cjk_ext.set(normalized)

    # --- о программе (24.10) ---

    @staticmethod
    def _version():
        try:
            from textools import __version__
            return __version__
        except Exception:
            return "?"

    @staticmethod
    def _dependency_rows():
        import importlib.metadata as md
        import importlib.util
        rows = [
            ("PyYAML", "yaml", False),
            ("python-docx", "docx", False),
            ("customtkinter", "customtkinter", False),
            ("pymorphy3", "pymorphy3", False),
            ("charset-normalizer", "charset_normalizer", False),
            ("tkinterdnd2", "tkinterdnd2", True),
        ]
        for dist, module, optional in rows:
            found = importlib.util.find_spec(module) is not None
            version = "?"
            if found:
                try:
                    version = md.version(dist)
                except Exception:
                    pass
            yield dist, found, version, optional

    def _check_deps(self):
        missing = 0
        for dist, found, version, optional in self._dependency_rows():
            if found:
                self._log(f"  {dist}: {version}\n", "ok")
            elif optional:
                self._log(f"  {dist}: не установлен (необязательно, "
                          "без него нет drag&drop)\n", "warn")
            else:
                missing += 1
                self._log(f"  {dist}: НЕ УСТАНОВЛЕН\n", "err")
        if missing:
            self._log(f"Не хватает обязательных пакетов: {missing}. "
                      "Установите: pip install -r requirements.txt\n", "err")
        else:
            self._log("Все обязательные зависимости на месте.\n", "ok")
        from gui_ctk import _app
        try:
            _app.status.configure(text="готов")
        except Exception:
            pass

    def _copy_info(self):
        import platform
        lines = [f"TextTools {self._version()}",
                 f"Python {platform.python_version()}",
                 f"ОС: {platform.system()} {platform.release()}"]
        for dist, found, version, optional in self._dependency_rows():
            state = version if found else ("нет (необязательно)" if optional
                                           else "НЕТ")
            lines.append(f"{dist}: {state}")
        text = "\n".join(lines)
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
            self._log("Сведения о системе скопированы в буфер обмена.\n", "ok")
        except Exception as e:
            self._log(f"Не удалось скопировать сведения: {e}\n", "err")

    def _open_readme(self):
        readme = CONFIG_FILE.parent / "README.md"
        if not readme.exists():
            self._log(f"README не найден: {readme}\n", "warn")
            return
        import os
        try:
            os.startfile(str(readme))
        except Exception as e:
            self._log(f"Не удалось открыть README: {e}\n", "err")

    def _open_project_dir(self):
        import os
        try:
            os.startfile(str(CONFIG_FILE.parent))
        except Exception as e:
            self._log(f"Не удалось открыть папку проекта: {e}\n", "err")

    def _check_scripts(self):
        # 20.10: проверка путей без запуска операций
        import wrappers as _wrappers
        from gui_config import CFG
        ok = miss = notset = 0
        for key in _wrappers.DEFAULTS:
            custom = CFG.get(f"script_{key}")
            if not custom:
                self._log(f"  {key}: не настроен\n", "warn")
                notset += 1
            elif Path(custom).is_file():
                self._log(f"  {key}: найден ({custom})\n", "ok")
                ok += 1
            else:
                self._log(f"  {key}: файл не найден ({custom})\n", "err")
                miss += 1
        if ok + miss == 0:
            self._log("Ни один внешний скрипт не настроен. Кнопки, которые "
                      "их используют, сообщат об этом в логе.\n", "warn")
        self._log(f"Итого: найдено {ok}, не найдено {miss}, не настроено "
                  f"{notset}.\n", "ok" if miss == 0 and notset == 0 else "warn")
        # 24.10: проверка путей не запускает процесс — возвращаем статус
        # «готов», а не оставляем код прошлой неудачной операции
        from gui_ctk import _app
        try:
            _app.status.configure(text="готов")
        except Exception:
            pass

    def _save_now(self):
        from gui_config import _load, CONFIG_FILE
        import json
        try:
            CONFIG_FILE.write_text(
                json.dumps(_load(), ensure_ascii=False, indent=2),
                encoding="utf-8")
            self._log("Настройки сохранены: ", "ok")
            self._log(f"{CONFIG_FILE}\n")
        except Exception as e:
            self._log(f"Ошибка сохранения: {e}\n", "err")

    def _run_backup(self):
        from gui_ctk import run_internal
        if not self.f_bak_dir.get():
            self._log("Укажите папку хранилища.\n")
            return
        args = ["--input", self.f_bak_dir.get()]
        if self.f_bak_file.get():
            args += ["--file", self.f_bak_file.get()]
        if self.c_bak_restore.get():
            args.append("--restore")
        run_internal("backup_restore", args)

    def _run_archive(self):
        from gui_ctk import run_internal
        if not self.f_bak_dir.get():
            self._log("Укажите папку хранилища.\n")
            return
        days = self.f_bak_days.get() or "30"
        if not days.isdigit() or int(days) < 1:
            self._log("«Старше (дней)»: введите целое число 1 или больше.\n",
                      "warn")
            return
        args = ["--input", self.f_bak_dir.get(), "--days", days]
        if self.c_bak_move.get():
            args.append("--move")
        run_internal("backup_archive", args)

    def _open_config(self):
        import subprocess
        subprocess.Popen(["notepad.exe", str(CONFIG_FILE)])

    def _open_history(self):
        from gui_ctk import HISTORY_FILE
        if not HISTORY_FILE.exists():
            self._log("Журнал пуст — ещё ни одной операции не было.\n")
            return
        import subprocess
        subprocess.Popen(["notepad.exe", str(HISTORY_FILE)])

    def _open_reports(self):
        # 24.10: учитываем папку отчётов из настроек
        from gui_ctk import _app
        import subprocess
        reports = _app._reports_dir()
        subprocess.Popen(["explorer", str(reports)])

    def _reset_geometry(self):
        from gui_ctk import _app
        try:
            _app.reset_geometry()
            self._log("Размер окна сброшен, окно поставлено по центру.\n",
                      "ok")
        except Exception as e:
            self._log(f"Не удалось сбросить размер окна: {e}\n", "err")

    def _open_guide(self):
        # 24.10: пошаговая инструкция по окну рядом с программой
        import os
        import subprocess
        guide = CONFIG_FILE.parent / "GUI_GUIDE.md"
        if not guide.exists():
            self._log(f"Инструкция не найдена: {guide}\n", "warn")
            return
        try:
            os.startfile(str(guide))
        except Exception:
            subprocess.Popen(["notepad.exe", str(guide)])

    def _open_parasites(self):
        from tools.text_stats import PARASITE_FILE, PARASITES
        if not PARASITE_FILE.exists():
            # 03.10: первый запуск — шаблон из встроенного списка
            # (файл полностью заменяет встроенный список)
            lines = [
                "# Слова-паразиты для статистики (вкладка «Хранилище»).",
                "# Если этот файл существует, он полностью заменяет встроенный",
                "# список. Формат — элементы YAML-списка, регистр не важен:",
                "#   - слово",
                "#   - составная фраза",
                "",
            ]
            lines += [f"- {p}" for p in PARASITES]
            PARASITE_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self._log(f"Создан шаблон списка паразитов: {PARASITE_FILE}\n")
        import subprocess
        subprocess.Popen(["notepad.exe", str(PARASITE_FILE)])

    def _reset_all(self):
        # 24.10: сброс удаляет файл настроек — спрашиваем подтверждение,
        # чтобы случайный клик не стёр пути к скриптам
        from tkinter import messagebox
        if not messagebox.askyesno(
                "Сброс настроек",
                "Очистить все сохранённые настройки?\n\n"
                "Пути, галочки и тема будут удалены. Тексты и бэкапы "
                "не затрагиваются.", icon="warning",
                parent=self.winfo_toplevel()):
            return
        import gui_config
        from gui_config import CONFIG_FILE
        if CONFIG_FILE.exists():
            try:
                CONFIG_FILE.unlink()
            except Exception as e:
                self._log(f"Ошибка сброса: {e}\n", "err")
                return
        # 20.10: конфиг в памяти тоже сбрасываем — иначе следующий ввод
        # в любом поле молча восстановит старые настройки
        gui_config.reset()
        self._log("Настройки сброшены. Перезапустите программу.\n", "ok")