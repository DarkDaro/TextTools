"""Вкладка «Чистка»: emoji-cleaner + clean_text_files + whitespace_clean.
18.09: переделана на CustomTkinter (widgets_ctk)."""
import customtkinter as ctk

from gui_config import CFG
from widgets_ctk import (PathField, CheckField, HelpBox, Section,
                         ActionButton, button_row, EntryField, FONT_SMALL)
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
            "• Эмодзи → SVG-иконки — заменяет эмодзи-иконки интерфейса на векторные "
            "SVG в html-файлах (вид одинаковый на любой системе).\n"
            "• Чистка разделителей — убирает строки-отбойники из повторяющихся "
            "символов (///// ***** ====== ———), к тексту они отношения не имеют.\n"
            "• АНТИРЕШИМОСТЬ — ищет запрещённую лексику памятки (решимость, "
            "лозунги, пафос) и умеет вырезать её с подсказками для ручной правки.\n"
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

        # 24.10: при восстановлении из .bak режим dry-run и бэкап
        # бессмысленны — гасим их, чтобы не путать
        def _sync_restore(*_):
            state = "disabled" if self.c_res.get() else "normal"
            try:
                self.c_dry.configure(state=state)
                self.c_bak.configure(state=state)
            except Exception:
                pass

        try:
            self.c_res.var.trace_add("write", _sync_restore)
        except Exception:
            pass
        _sync_restore()

        row1 = button_row(s1.inner)
        self.b_emoji = ActionButton(
            row1, "Запустить чистку эмодзи", self._run_emoji,
            kind="safe", width=235,
            tooltip="Удаляет эмодзи и текстовые смайлы. Шахматы, ноты "
                    "и масти карт не трогаются.")
        self.b_emoji.pack(side="left")

        # 24.10: кнопка краснеет, если возможна реальная запись —
        # снят dry-run или включено восстановление из .bak
        def _sync_emoji(*_):
            risky = bool(self.c_res.get()) or not bool(self.c_dry.get())
            self.b_emoji.set_kind("danger" if risky else "safe")
        for _v in (self.c_dry.var, self.c_res.var):
            try:
                _v.trace_add("write", _sync_emoji)
            except Exception:
                pass
        _sync_emoji()

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
        row2 = button_row(s2.inner)
        b_text = ActionButton(
            row2, "Запустить чистку мусора", self._run_clean_text,
            kind="safe", width=235,
            tooltip="Удаляет служебный мусор и CJK-символы по белому списку разрешённых.")
        b_text.pack(side="left")
        b_text.link_danger(self.c_fix.var)

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
        row3 = button_row(s3.inner)
        b_ws = ActionButton(
            row3, "Запустить чистку пробелов", self._run_whitespace,
            kind="safe", width=235,
            tooltip="Хвосты пробелов, табы, лишние пустые строки. "
                    "Код-блоки не трогаются.")
        b_ws.pack(side="left")
        b_ws.link_danger(self.c_ws_fix.var)

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
        row4 = button_row(s4.inner)
        b_utf8 = ActionButton(
            row4, "Проверить кодировки", self._run_utf8,
            kind="safe", width=235,
            tooltip="Покажет, какие файлы не в UTF-8; с галочкой «Применить» — "
                    "перекодирует (koi8-r, cp1251 и т.п.).")
        b_utf8.pack(side="left")
        b_utf8.link_danger(self.c_utf8_fix.var)

        # --- 5. типографика (03.10) ---
        s5 = Section(parent, "5. Типографика: «ёлочки», тире, многоточия (txt / md / docx)")
        self.f_typo = PathField(s5.inner, "Папка или файл:", "typo_input", CFG,
                                file_mode="both",
                                tooltip="Папка (обход рекурсивный) или один файл "
                                        ".md/.txt/.docx.")
        r5 = ctk.CTkFrame(s5.inner, fg_color="transparent")
        r5.pack(fill="x", pady=4)
        self.c_typo_fix = CheckField(r5, "Применить изменения", "typo_fix", CFG,
                                     default=False,
                                     tooltip="Без галочки — dry-run (только отчёт). "
                                             "С галочкой — реально правит, "
                                             "создавая .bak рядом с файлом.")
        self.c_typo_fix.pack(side="left", padx=(0, 16))
        self.c_typo_nbsp = CheckField(r5, "Неразрывные пробелы", "typo_nbsp", CFG,
                                      default=False,
                                      tooltip="Ставит неразрывный пробел после "
                                              "предлогов/союзов (в, и, с, на…) "
                                              "и после «№». По умолчанию выключено.")
        self.c_typo_nbsp.pack(side="left", padx=16)
        ctk.CTkLabel(s5.inner, justify="left", anchor="w", font=FONT_SMALL, text=(
            "Кавычки \"...\" → «ёлочки» (парные, вокруг кириллицы), "
            "3+ точки → …, «слово - слово» → «слово — слово», "
            "«- Реплика» в начале строки → «— Реплика» (txt/docx; в .md списки "
            "не трогаются). Код-блоки, frontmatter и inline-код не трогаются."
        )).pack(anchor="w", pady=(0, 2))
        row5 = button_row(s5.inner)
        b_typo = ActionButton(
            row5, "Запустить типографику", self._run_typo,
            kind="safe", width=235,
            tooltip="«Ёлочки», тире, многоточия, неразрывные пробелы (опция). "
                    "Dry-run по умолчанию.")
        b_typo.pack(side="left")
        b_typo.link_danger(self.c_typo_fix.var)

        # --- 6. эмодзи → SVG-иконки в html (04.11) ---
        s6 = Section(parent, "6. Эмодзи → SVG-иконки в интерфейсе (html)")
        self.f_icons = PathField(s6.inner, "Папка или файл:", "icons_input", CFG,
                                 file_mode="both",
                                 tooltip="HTML-файл или папка с html-файлами "
                                         "(обход рекурсивный).")
        r6 = ctk.CTkFrame(s6.inner, fg_color="transparent")
        r6.pack(fill="x", pady=4)
        self.c_icons_fix = CheckField(r6, "Применить изменения", "icons_fix", CFG,
                                      default=False,
                                      tooltip="Без галочки — отчёт: какие файлы "
                                              "и сколько иконок будут заменены. "
                                              "С галочкой — замена, копия .bak "
                                              "рядом с файлом.")
        self.c_icons_fix.pack(side="left", padx=(0, 16))
        self.c_icons_nobak = CheckField(r6, "Без бэкапа .bak", "icons_no_bak", CFG,
                                        default=False,
                                        tooltip="Для папок под git: копии .bak "
                                                "не создаются. Внимание: без "
                                                "бэкапа откатить замену нечем.")
        self.c_icons_nobak.pack(side="left", padx=16)
        ctk.CTkLabel(s6.inner, justify="left", anchor="w", font=FONT_SMALL, text=(
            "Эмодзи-иконки интерфейса (💰 ❤️ ⏩ 🔊 …) заменяются на векторные "
            "SVG: вид одинаковый на любой системе и не зависит от шрифтов "
            "эмодзи. Повторный запуск безопасен — уже обработанные файлы "
            "пропускаются. Свой набор замен — ключ --map в командной строке."
        )).pack(anchor="w", pady=(0, 2))
        row6 = button_row(s6.inner)
        b_icons = ActionButton(
            row6, "Заменить иконки", self._run_icons,
            kind="safe", width=235,
            tooltip="Эмодзи-иконки → SVG в html. Dry-run по умолчанию, "
                    "с галочкой «Применить» — замена с .bak.")
        b_icons.pack(side="left")
        b_icons.link_danger(self.c_icons_fix.var)

        # --- 7. мусорные разделители (04.11) ---
        s7 = Section(parent, "7. Чистка мусорных разделителей (txt / md / docx)")
        self.f_sep = PathField(s7.inner, "Папка или файл:", "sep_input", CFG,
                               file_mode="both",
                               tooltip="Папка (обход рекурсивный) или один файл "
                                       ".md/.txt/.docx.")
        self.c_sep_fix = CheckField(s7.inner, "Применить изменения", "sep_fix",
                                    CFG, default=False,
                                    tooltip="Без галочки — dry-run (только отчёт). "
                                            "С галочкой — реально чистит, "
                                            "создавая .bak рядом с файлом.")
        self.c_sep_fix.pack(anchor="w")
        self.e_sep_min = EntryField(s7.inner, "Минимальная серия:",
                                    "sep_min_run", CFG,
                                    width_label=160, placeholder="3",
                                    tooltip="Сколько одинаковых символов подряд "
                                            "считать разделителем. "
                                            "Пусто — 3 (по умолчанию).")
        self.e_sep_syms = EntryField(s7.inner, "Символы разделителей:",
                                     "sep_symbols", CFG,
                                     width_label=160,
                                     placeholder="*/=~-_+%&@•·—–§",
                                     tooltip="Из каких символов может состоять "
                                             "строка-разделитель. Пусто — набор "
                                             "по умолчанию.")
        ctk.CTkLabel(s7.inner, justify="left", anchor="w", font=FONT_SMALL, text=(
            "Убирает строки-отбойники из повторяющихся символов: /////, *****, "
            "======, ———, * * *. Frontmatter, код-блоки, заголовки из решёток "
            "и таблицы не трогаются. На месте разделителя остаётся пустая "
            "строка — текст не склеивается."
        )).pack(anchor="w", pady=(0, 2))
        row7 = button_row(s7.inner)
        b_sep = ActionButton(
            row7, "Запустить чистку разделителей", self._run_sep,
            kind="safe", width=235,
            tooltip="Строки из повторяющихся символов (///// ***** ======). "
                    "Dry-run по умолчанию, с галочкой «Применить» — "
                    "правка с .bak.")
        b_sep.pack(side="left")
        b_sep.link_danger(self.c_sep_fix.var)

        # --- 8. АНТИРЕШИМОСТЬ (05.11) ---
        s8 = Section(parent,
                     "8. АНТИРЕШИМОСТЬ — запрещённая лексика и пафос "
                     "(txt / md / docx)")
        self.f_ar = PathField(s8.inner, "Папка или файл:", "ar_input", CFG,
                              file_mode="both",
                              tooltip="Папка (обход рекурсивный) или один файл "
                                      ".md/.txt/.docx.")
        self.c_ar_fix = CheckField(s8.inner, "Зачистить (вырезать hard)",
                                   "ar_clean", CFG, default=False,
                                   tooltip="Без галочки — только поиск, лог и "
                                           "отчёт. С галочкой — вырезает жёсткие "
                                           "вхождения (решимость, лозунги, "
                                           "превозмогание…), создавая .bak рядом "
                                           "с файлом. soft-слова (надежда, "
                                           "штампы) только подсвечиваются — "
                                           "решает автор.")
        self.c_ar_fix.pack(anchor="w")
        ctk.CTkLabel(s8.inner, justify="left", anchor="w", font=FONT_SMALL, text=(
            "Словари: data/resolve_db.yaml (лексика памятки) и "
            "data/pathos_db.yaml (антипафос) — правятся вручную. Находки с "
            "подсказками («Она смотрела в одну точку. Не мигала») дописываются "
            "в лог reports/antiresolve.log. Эмоции — через действие."
        )).pack(anchor="w", pady=(0, 2))
        row8 = button_row(s8.inner)
        b_ar = ActionButton(
            row8, "Запустить АНТИРЕШИМОСТЬ", self._run_ar,
            kind="safe", width=235,
            tooltip="Поиск запрещённой лексики и пафоса. С галочкой "
                    "«Зачистить» — правка с .bak.")
        b_ar.pack(side="left")
        b_ar.link_danger(self.c_ar_fix.var)

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

    def _run_typo(self):
        from gui_ctk import run_internal
        p = self.f_typo.get()
        if not p:
            self._log("Укажите папку или файл.\n")
            return
        args = ["--input", p]
        if self.c_typo_fix.get():
            args.append("--fix")
        if self.c_typo_nbsp.get():
            args.append("--nbsp")
        run_internal("typography", args)

    def _run_icons(self):
        from gui_ctk import run_internal
        p = self.f_icons.get()
        if not p:
            self._log("Укажите папку или файл.\n")
            return
        args = ["--input", p]
        if self.c_icons_fix.get():
            args.append("--fix")
        if self.c_icons_nobak.get():
            args.append("--no-bak")
        run_internal("icon_replace", args)

    def _run_sep(self):
        from gui_ctk import run_internal
        p = self.f_sep.get()
        if not p:
            self._log("Укажите папку или файл.\n")
            return
        args = ["--input", p]
        if self.c_sep_fix.get():
            args.append("--fix")
        min_run = self.e_sep_min.get()
        if min_run and not min_run.isdigit():
            self._log("Минимальная серия — целое число, например 3.\n")
            return
        if min_run:
            args += ["--min-run", min_run]
        syms = self.e_sep_syms.get()
        if syms:
            args += ["--symbols", syms]
        run_internal("separator_clean", args)

    def _run_ar(self):
        from gui_ctk import run_internal
        p = self.f_ar.get()
        if not p:
            self._log("Укажите папку или файл.\n")
            return
        args = ["--input", p]
        if self.c_ar_fix.get():
            args.append("--clean")
        run_internal("antiresolve", args)

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