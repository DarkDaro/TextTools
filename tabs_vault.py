"""Вкладка «Хранилище»: orphan-finder, broken-links, merge-finder, integrity,
obsidian-check и поиск иероглифов (find_cjk).
18.09: переделана на CustomTkinter (widgets_ctk).
05.11: штампы, статистика и стилистика переехали во вкладку «Писателям»
(tabs_writers) — вкладка стала чисто «хранилищной»."""
from pathlib import Path

import customtkinter as ctk

from gui_config import CFG
from widgets_ctk import (PathField, CheckField, HelpBox, Section,
                         ActionButton, button_row)

HERE = Path(__file__).resolve().parent


class VaultTab(ctk.CTkFrame):
    LABEL = "Хранилище"

    def _build(self, parent):
        HelpBox(parent, text=(
            "Как это работает:\n"
            "Укажите папку хранилища (vault) — инструмент обойдёт все .md/.txt/.docx файлы внутри.\n"
            "• Orphans — заметки, на которые никто не ссылается и которые сами ни на кого не ссылаются "
            "(одиночки, возможно забыты).\n"
            "• Битые ссылки — ссылки [[вот так]], ведущие на несуществующую заметку.\n"
            "• Дубликаты — заметки с очень похожим содержимым или почти одинаковым именем — "
            "кандидаты на слияние (ищутся и в Word-файлах .docx).\n"
            "• Целостность — пустые файлы, битая кодировка, незакрытый frontmatter, "
            "отсутствие заголовка.\n"
            "• Валидатор Obsidian — всё то, что Obsidian молча ломает при чтении: "
            "таблицы, заголовки, теги, ссылки, code fence. По умолчанию только читает; "
            "галочка «Исправить однозначное» включает запись с бэкапом .bak.\n"
            "• Иероглифы — китайские знаки, японские азбуки, мойбейк и невидимые "
            "символы: частая порча текста после языковых моделей.\n"
            "Все проверки, кроме «Исправить однозначное», ТОЛЬКО читают файлы."))

        s = Section(parent, "Хранилище (vault)")
        self.f_vault = PathField(s.inner, "Папка vault:", "vault_input", CFG,
                                 file_mode="both",
                                 tooltip="Обычно это папка хранилища Obsidian "
                                         "(например Daro Coding) — обход рекурсивный. "
                                         "Но можно выбрать и один .md файл — "
                                         "инструмент проверит только его.")

        btns = button_row(s.inner, pady=(6, 0))
        ActionButton(btns, "Orphans", self._run_orphans,
                     kind="safe", width=130,
                     tooltip="Заметки без входящих и исходящих ссылок."
                     ).pack(side="left", padx=(0, 8))
        ActionButton(btns, "Битые ссылки", self._run_broken,
                     kind="safe", width=145,
                     tooltip="Ссылки [[такие]], ведущие на несуществующие заметки."
                     ).pack(side="left", padx=(0, 8))
        ActionButton(btns, "Дубликаты", self._run_merge,
                     kind="safe", width=140,
                     tooltip="Похожие заметки (.md/.txt/.docx) — кандидаты "
                             "на слияние."
                     ).pack(side="left", padx=(0, 8))
        ActionButton(btns, "Целостность", self._run_integrity,
                     kind="safe", width=145,
                     tooltip="Пустые файлы, битый UTF-8, незакрытый frontmatter, "
                             "отсутствие заголовка ##. Только чтение."
                     ).pack(side="left")

        # 04.11: профиль «проверить всё»; 05.11 — уже шесть проверок:
        # добавлены штампы ИИ и АНТИРЕШИМОСТЬ в скан-режиме
        row_all = button_row(s.inner)
        ActionButton(row_all, "Проверить всё (6 проверок)", self._run_fullcheck,
                     kind="safe", width=235,
                     tooltip="валидатор Obsidian → иероглифы → целостность → "
                             "дубликаты → штампы ИИ (скан) → АНТИРЕШИМОСТЬ "
                             "(скан, без зачистки). Только чтение, сводка "
                             "в журнале. Серьёзные находки (валидатор, "
                             "иероглифы, целостность) — статус «есть замечания».").pack(side="left")

        self.c_report = CheckField(s.inner, "Сохранять отчёт в папку отчётов",
                                   "vault_save_report", CFG,
                                   tooltip="Кроме окна, отчёт будет записан "
                                           "в папку отчётов (по умолчанию "
                                           "reports/ внутри textools).")
        self.c_report.pack(anchor="w", pady=(0, 4))

        # --- 24.10: валидатор метафайлов Obsidian ---
        s_obs = Section(parent, "Валидатор заметок Obsidian (obsidian-check)")
        self.f_obs = PathField(s_obs.inner, "Папка vault:", "obs_input", CFG,
                               file_mode="both",
                               tooltip="Папка хранилища или одна заметка. "
                                       "Проверяет frontmatter, таблицы, "
                                       "заголовки, теги, ссылки и code fence.")
        r_obs = ctk.CTkFrame(s_obs.inner, fg_color="transparent")
        r_obs.pack(fill="x", pady=4)
        self.c_obs_fix = CheckField(r_obs, "Исправить однозначное (--fix)",
                                    "obs_fix", CFG, default=False,
                                    tooltip="Правит только машинно-однозначное: "
                                            "кавычки в значениях frontmatter, "
                                            "'|' внутри `кода` в таблице, "
                                            "посимвольно разбитый текст. "
                                            "Перед записью создаётся .bak.")
        self.c_obs_fix.pack(side="left", padx=(0, 16))
        self.c_obs_report = CheckField(r_obs, "Сохранять отчёт в папку отчётов",
                                       "obs_report", CFG, default=False,
                                       tooltip="Пишет полный отчёт со всеми "
                                               "замечаниями в папку отчётов "
                                               "(по умолчанию reports/).")
        self.c_obs_report.pack(side="left", padx=16)
        row_obs = button_row(s_obs.inner)
        b_obs = ActionButton(row_obs, "Проверить заметки", self._run_obsidian,
                             kind="safe", width=185,
                             tooltip="ERROR — Obsidian отрисует неверно или "
                                     "потеряет данные, WARN — сломана структура, "
                                     "INFO — косметика. Без галочки только читает.")
        b_obs.pack(side="left")
        b_obs.link_danger(self.c_obs_fix.var)

        # --- 24.10: поиск иероглифов и порчи кодировки (find_cjk) ---
        s_cjk = Section(parent, "Иероглифы и порча кодировки (find_cjk)")
        self.f_cjk = PathField(s_cjk.inner, "Папка или файл:", "cjk_input", CFG,
                               file_mode="both",
                               tooltip="Проверяет .md/.txt/.json/.yaml на китайские "
                                       "иероглифы, японские и корейские азбуки, "
                                       "мойбейк, невидимые символы. Только чтение.")
        self.c_cjk_json = CheckField(s_cjk.inner,
                                     "Сохранять полный отчёт в JSON",
                                     "cjk_json", CFG, default=False,
                                     tooltip="JSON со всеми находками (файл, "
                                             "строка, колонка, код символа) "
                                             "в папке отчётов.")
        self.c_cjk_json.pack(anchor="w")
        row_cjk = button_row(s_cjk.inner)
        ActionButton(row_cjk, "Найти иероглифы", self._run_cjk,
                     kind="safe", width=185,
                     tooltip="Иероглифы, мойбейк (UTF-8, прочитанный как "
                             "latin-1/cp1251) и BOM внутри текста. "
                             "Файлы не меняются.").pack(side="left")

        # 05.11: штампы, статистика и стилистика переехали во вкладку
        # «Писателям» (tabs_writers)

    def _run(self, modname):
        from gui_ctk import run_internal, _app
        path = self.f_vault.get()
        if not path:
            _app.log_line("Укажите папку vault.\n")
            return
        args = ["--input", path]
        # 18.09: vault_save_report теперь реально пишет отчёт в reports/
        if self.c_report.get():
            # 24.10: учитываем папку отчётов из настроек
            from gui_ctk import _app
            reports = _app._reports_dir()
            args += ["--out", str(reports / f"{modname}.md")]
        run_internal(modname, args)

    def _run_fullcheck(self):
        # 04.11: профиль «проверить всё» — full_check по пути f_vault
        from gui_ctk import run_internal, _app
        path = self.f_vault.get()
        if not path:
            _app.log_line("Укажите папку vault.\n")
            return
        run_internal("full_check", ["--input", path])

    def _run_orphans(self):
        self._run("orphan_finder")

    def _run_broken(self):
        self._run("broken_links")

    def _run_merge(self):
        self._run("merge_finder")

    def _run_integrity(self):
        self._run("integrity_check")

    def _run_obsidian(self):
        # 24.10: валидатор метафайлов Obsidian; --fix только по галочке
        from gui_ctk import run_internal, _app
        p = self.f_obs.get()
        if not p:
            _app.log_line("Укажите папку vault для проверки Obsidian.\n")
            return
        args = ["--input", p]
        # 04.11: без --exit-zero — код 1 при ERROR теперь показывается
        # как «есть замечания», а не «Готово» (раньше статус противоречил
        # содержимому журнала)
        if self.c_obs_fix.get():
            args.append("--fix")
            # 24.10: настройка «не создавать .bak» (папки под git).
            # 04.11: значение могло прийти строкой («true» из правки
            # руками) — строгий `is True` молча игнорировал его
            from gui_ctk import _cfg_flag
            if _cfg_flag("obs_no_bak", False):
                args.append("--no-bak")
        if self.c_obs_report.get():
            reports = _app._reports_dir()
            args += ["--out", str(reports / "obsidian-check.md")]
        run_internal("obsidian_check", args)

    def _run_cjk(self):
        # 24.10: find_cjk живёт в корне проекта, запуск отдельным процессом
        from gui_ctk import run_cmd, _app
        p = self.f_cjk.get()
        if not p:
            _app.log_line("Укажите папку или файл для поиска иероглифов.\n")
            return
        # 25.10: код 1 у find_cjk — находки. GUI показывает статус
        # «есть замечания», поэтому --exit-zero здесь не нужен.
        # 26.10: tool_cmd покрывает exe (self-run) и обычный запуск
        from gui_ctk import tool_cmd
        cmd = tool_cmd("find_cjk", p)
        ext = str(CFG.get("cjk_ext", "") or "").strip()
        if ext:
            cmd += ["--ext", ext]
        if self.c_cjk_json.get():
            reports = _app._reports_dir()
            cmd += ["--json", str(reports / "cjk_report.json")]
        run_cmd(cmd)
