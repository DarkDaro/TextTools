"""Вкладка «Настройки»: пути к внешним скриптам, общие параметры.
18.09: переделана на CustomTkinter (widgets_ctk)."""
import customtkinter as ctk

from gui_config import CFG, CONFIG_FILE
from widgets_ctk import (PathField, EntryField, CheckField, HelpBox,
                         Section, BigButton, Tooltip, FONT_SMALL)
from wrappers import DEFAULTS


class SettingsTab(ctk.CTkFrame):
    LABEL = "Настройки"

    def _build(self, parent):
        HelpBox(parent, text=(
            "Здесь настраиваются пути к внешним скриптам (обычно менять не нужно — "
            "уже стоят правильные) и хранилище по умолчанию. "
            "Все настройки сохраняются автоматически."))

        s1 = Section(parent, "Пути к внешним скриптам")
        for label, key in (("emoji-cleaner:", "emoji_cleaner"),
                           ("clean_text_files:", "clean_text"),
                           ("md_replace:", "md_replace"),
                           ("char_search:", "char_search"),
                           ("refile:", "refile")):
            PathField(s1.inner, label, f"script_{key}", CFG, file_mode="file",
                      tooltip=f"Путь к скрипту. По умолчанию: {DEFAULTS[key]}")

        s2 = Section(parent, "Общее")
        PathField(s2.inner, "Vault по умолчанию:", "default_vault", CFG, file_mode="dir",
                  tooltip="Подставляется в поля хранилища на других вкладках, "
                          "если они пустые.")
        CheckField(s2.inner, "Показывать команды в логе", "show_cmd", CFG, default=True,
                   tooltip="Показывать в окне вывода командную строку перед результатом."
                   ).pack(anchor="w")

        # --- Сохранение / сброс ---
        s3 = Section(parent, "Сохранение настроек")
        ctk.CTkLabel(s3.inner, justify="left", anchor="w", font=FONT_SMALL, text=(
            "Все настройки сохраняются автоматически при каждом изменении "
            "(путь, галочка, тема). Кнопки ниже — для ручного управления."
        )).pack(anchor="w", pady=(0, 4))
        r3 = ctk.CTkFrame(s3.inner, fg_color="transparent")
        r3.pack(fill="x", pady=2)
        BigButton(r3, "Сохранить сейчас", self._save_now,
                  tooltip="Принудительно записать все текущие значения в gui_config.json."
                  ).pack(side="left", padx=(0, 8))
        b_open = ctk.CTkButton(r3, text="Открыть конфиг", height=34,
                               command=self._open_config)
        b_open.pack(side="left", padx=8)
        Tooltip(b_open, "Открыть файл настроек в Блокноте. "
                        "Можно править вручную; изменения подхватятся после перезапуска.")
        b_reset = ctk.CTkButton(r3, text="Сбросить всё", height=34,
                                command=self._reset_all)
        b_reset.pack(side="left", padx=8)
        Tooltip(b_reset, "Очистить все сохранённые настройки (пути, галочки, тема). "
                         "Окно можно закрыть и открыть заново — поля будут пустыми.")

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
        BigButton(s_bak.inner, "Показать / восстановить бэкапы", self._run_backup,
                  tooltip="Обзор всех бэкапов; с галочкой «Восстановить» — "
                          "откат к прежнему содержимому.")
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
        BigButton(s_bak.inner, "Показать старые бэкапы / Архивировать", self._run_archive,
                  tooltip="Бэкапы старше N дней переносятся в централизованный "
                          "архив textools — с сохранением структуры и без "
                          "перезаписи.")

        # --- Журнал операций (02.10) ---
        s_h = Section(parent, "Журнал операций")
        ctk.CTkLabel(s_h.inner, justify="left", anchor="w", font=FONT_SMALL, text=(
            "Каждый запуск инструмента из GUI пишется в logs/history.log: "
            "время, команда, код завершения и длительность. "
            "Удобно вспомнить, что и когда делалось с текстами."
        )).pack(anchor="w", pady=(0, 4))
        b_hist = ctk.CTkButton(s_h.inner, text="Открыть журнал", height=34,
                               command=self._open_history)
        b_hist.pack(anchor="w")
        Tooltip(b_hist, "Открыть logs/history.log в Блокноте. "
                        "Файл можно удалять целиком — при следующей операции "
                        "он создастся заново.")

        s4 = Section(parent, "Информация")
        ctk.CTkLabel(s4.inner, justify="left", anchor="w", font=FONT_SMALL, text=(
            f"Настройки хранятся в: {CONFIG_FILE}\n"
            "Отчёты сохраняются в: reports/ (рядом с программой)\n\n"
            "Безопасность:\n"
            "  • Всё, что меняет файлы, по умолчанию в dry-run (только отчёт)\n"
            "  • Реальная запись — только явный чекбокс «Применить изменения»\n"
            "  • Бэкапы: .bak рядом с файлами или md_replace_backups в хранилище\n"
            "  • Кнопка «Стоп» внизу окна прерывает запущенную операцию"
        )).pack(anchor="w")
        r4 = ctk.CTkFrame(s4.inner, fg_color="transparent")
        r4.pack(fill="x", pady=(6, 0))
        b_rep = ctk.CTkButton(r4, text="Открыть папку отчётов", height=34,
                              command=self._open_reports)
        b_rep.pack(side="left", padx=(0, 8))
        Tooltip(b_rep, "reports/ — сюда пишутся отчёты инструментов "
                       "(когда включено «Сохранять отчёт»).")
        b_par = ctk.CTkButton(r4, text="Открыть список паразитов", height=34,
                              command=self._open_parasites)
        b_par.pack(side="left", padx=8)
        Tooltip(b_par, "tools/parasites.yaml — свой список слов-паразитов "
                       "для статистики. При первом открытии создаётся шаблон "
                       "из встроенного списка.")

    def _log(self, msg, tag=None):
        from gui_ctk import _app
        _app.log_line(msg, tag)

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
        args = ["--input", self.f_bak_dir.get(),
                "--days", self.f_bak_days.get() or "30"]
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
        from gui_ctk import REPORTS_DIR
        REPORTS_DIR.mkdir(exist_ok=True)
        import subprocess
        subprocess.Popen(["explorer", str(REPORTS_DIR)])

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
        from gui_config import CONFIG_FILE
        if CONFIG_FILE.exists():
            try:
                CONFIG_FILE.unlink()
            except Exception as e:
                self._log(f"Ошибка сброса: {e}\n", "err")
                return
        self._log("Настройки сброшены. Перезапустите программу.\n", "ok")