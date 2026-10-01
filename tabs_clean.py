"""Вкладка «Чистка»: emoji-cleaner + clean_text_files + whitespace_clean.
18.09: переделана на CustomTkinter (widgets_ctk)."""
import customtkinter as ctk

from gui_config import CFG
from widgets_ctk import (PathField, CheckField, HelpBox, Section,
                         BigButton, FONT_SMALL)
from wrappers import cmd_emoji_clean, cmd_clean_text


class CleanTab(ctk.CTkFrame):
    LABEL = "Чистка"

    def _build(self, parent):
        HelpBox(parent, text=(
            "Как это работает:\n"
            "• Чистка эмодзи — удаляет эмодзи и текстовые смайлы из .txt/.md/.docx. "
            "Шахматы, ноты, масти карт и Mac-символы НЕ трогаются.\n"
            "• Чистка мусора — удаляет служебный мусор и CJK-символы (китайские/японские) "
            "из .txt/.md по белому списку разрешённых символов.\n"
            "Безопасность: по умолчанию всё в режиме dry-run (только отчёт). "
            "Чтобы реально изменить файлы — снимите dry-run / поставьте «Применить». "
            "С бэкапом (.bak рядом с файлом) всегда можно откатить."))

        # --- emoji ---
        s1 = Section(parent, "1. Чистка эмодзи и смайлов (txt / md / docx)")
        self.f_emoji = PathField(s1.inner, "Папка или файл:", "clean_emoji_input", CFG,
                                 file_mode="both",
                                 tooltip="Можно выбрать как папку (обработаются все "
                                         "txt/md/docx внутри), так и один файл.")
        r1 = ctk.CTkFrame(s1.inner, fg_color="transparent")
        r1.pack(fill="x", pady=4)
        self.c_dry = CheckField(r1, "Только отчёт (dry-run)", "emoji_dry_run", CFG,
                                default=True,
                                tooltip="Файлы не изменяются, показывается, что было бы удалено.")
        self.c_dry.pack(side="left", padx=(0, 16))
        self.c_bak = CheckField(r1, "Бэкап .bak", "emoji_backup", CFG, default=False,
                                tooltip="Перед изменением рядом с файлом создаётся копия "
                                        "<имя>.bak. Откат — кнопкой ниже.")
        self.c_bak.pack(side="left", padx=16)
        self.c_res = CheckField(r1, "Восстановить из .bak", "emoji_restore", CFG,
                                default=False,
                                tooltip="Откат: вернуть содержимое из копий .bak. "
                                        "Сами копии не удаляются.")
        self.c_res.pack(side="left", padx=16)

        BigButton(s1.inner, "Запустить чистку эмодзи", self._run_emoji)

        # --- clean_text_files ---
        s2 = Section(parent, "2. Чистка мусора и CJK-символов (txt / md)")
        self.f_text = PathField(s2.inner, "Папка:", "clean_text_input", CFG,
                                file_mode="both",
                                tooltip="Папка с txt/md файлами. Обход рекурсивный.")
        self.c_fix = CheckField(s2.inner, "Применить изменения (--fix)", "clean_text_fix",
                                CFG, default=False,
                                tooltip="Без галочки — только отчёт. С галочкой — "
                                        "реально чистит, создавая .bak бэкапы.")
        self.c_fix.pack(anchor="w")
        ctk.CTkLabel(s2.inner, justify="left", anchor="w", font=FONT_SMALL,
                     text="Без галочки — только отчёт (что было бы удалено), файлы не меняются."
                     ).pack(anchor="w")
        BigButton(s2.inner, "Запустить чистку мусора", self._run_clean_text)

        # --- whitespace_clean (18.09) ---
        s3 = Section(parent, "3. Чистка пробелов и пустых строк (txt / md / docx)")
        self.f_ws = PathField(s3.inner, "Папка или файл:", "ws_input", CFG,
                              file_mode="both",
                              tooltip="Папка (обход рекурсивный) или один файл "
                                      ".md/.txt/.docx.")
        r3 = ctk.CTkFrame(s3.inner, fg_color="transparent")
        r3.pack(fill="x", pady=4)
        self.c_ws_fix = CheckField(r3, "Применить изменения", "ws_fix", CFG,
                                   default=False,
                                   tooltip="Без галочки — dry-run (только отчёт). "
                                           "С галочкой — реально правит, "
                                           "создавая .bak рядом с файлом.")
        self.c_ws_fix.pack(side="left", padx=(0, 16))
        self.c_ws_breaks = CheckField(r3, "Сохранять переносы (2 пробела)",
                                      "ws_keep_breaks", CFG, default=False,
                                      tooltip="Markdown-перенос строки — два пробела "
                                              "в конце строки. Без галочки они "
                                              "удаляются как обычные пробелы.")
        self.c_ws_breaks.pack(side="left", padx=16)
        ctk.CTkLabel(s3.inner, justify="left", anchor="w", font=FONT_SMALL, text=(
            "Убирает: пробелы/табы в конце строк, лишние пустые строки "
            "(оставляет одну между абзацами), пустые строки в начале файла. "
            "Блоки кода ``` не трогаются. В docx правится только текст — "
            "форматирование (жирный, курсив, таблицы) сохраняется."
        )).pack(anchor="w", pady=(0, 2))
        BigButton(s3.inner, "Запустить чистку пробелов", self._run_whitespace)

        # --- 4. кодировки (01.10) ---
        s4 = Section(parent, "4. Кодировки: приведение к UTF-8 (txt / md)")
        self.f_utf8 = PathField(s4.inner, "Папка или файл:", "utf8_input", CFG,
                                file_mode="both",
                                tooltip="Старые файлы (koi8-r, cp1251…) "
                                        "перекодируются в UTF-8. .docx — "
                                        "это zip, к нему не применяется.")
        self.c_utf8_fix = CheckField(s4.inner, "Применить изменения",
                                     "utf8_fix", CFG, default=False,
                                     tooltip="Без галочки — отчёт «в какой "
                                             "кодировке что». С галочкой — "
                                             "перекодирует (с .bak).")
        self.c_utf8_fix.pack(anchor="w")
        BigButton(s4.inner, "Проверить кодировки", self._run_utf8)

    def _log(self, msg):
        from gui_ctk import _app
        _app.log_line(msg)

    def _run_whitespace(self):
        from gui_ctk import run_internal
        p = self.f_ws.get()
        if not p:
            self._log("Укажите папку или файл.\n")
            return
        args = ["--input", p]
        if self.c_ws_fix.get():
            args.append("--fix")
        if self.c_ws_breaks.get():
            args.append("--keep-breaks")
        run_internal("whitespace_clean", args)

    def _run_utf8(self):
        from gui_ctk import run_internal
        p = self.f_utf8.get()
        if not p:
            self._log("Укажите папку или файл.\n")
            return
        args = ["--input", p]
        if self.c_utf8_fix.get():
            args.append("--fix")
        run_internal("utf8_convert", args)

    def _run_emoji(self):
        p = self.f_emoji.get()
        if not p:
            self._log("Укажите папку или файл.\n")
            return
        from gui_ctk import run_cmd
        run_cmd(cmd_emoji_clean([p],
                                dry_run=self.c_dry.get(),
                                backup=self.c_bak.get(),
                                restore=self.c_res.get()))

    def _run_clean_text(self):
        p = self.f_text.get()
        if not p:
            self._log("Укажите папку.\n")
            return
        from gui_ctk import run_cmd
        run_cmd(cmd_clean_text(p, apply=self.c_fix.get()))