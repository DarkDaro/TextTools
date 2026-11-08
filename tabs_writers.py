"""Вкладка «Писателям»: инструменты для работы с большим текстом.
05.11: выделена из «Чистки» (АНТИРЕШИМОСТЬ), «Хранилища» (штампы,
статистика, стилистика) и «Имён» (Ё/Е-аудит), чтобы разгрузить основные
вкладки и собрать писательский цикл в одном месте.

Здесь живёт редакторский цикл рукописи: стиль (АНТИРЕШИМОСТЬ) →
штампы и канцелярит → повторы и длинные предложения → объём и паразиты →
вычитка ё/е. Ключи конфига полей не менялись (ar_input, pc_input,
style_input, stats_input, yo_input) — история путей и галочки
переносятся вместе с инструментами."""
import customtkinter as ctk

from gui_config import CFG
from widgets_ctk import (PathField, CheckField, HelpBox, Section,
                         ActionButton, button_row, EntryField, FONT_SMALL)


class WritersTab(ctk.CTkFrame):
    LABEL = "Писателям"

    def _build(self, parent):
        HelpBox(parent, text=(
            "Как это работает:\n"
            "Вкладка собрана для работы с рукописью — романом, повестью, "
            "длинными текстами. Сверху вниз — редакторский цикл:\n"
            "• АНТИРЕШИМОСТЬ — ищет запрещённую лексику памятки (решимость, "
            "лозунги, пафос) и умеет вырезать её с подсказками для ручной правки. "
            "Эмоции — через действие, а не через выводы.\n"
            "• Штампы ИИ-текста и канцелярит — находит шаблонные обороты "
            "(«стоит отметить, что», «в современном мире»); чистит по словарю "
            "или выборочно через витрину.\n"
            "• Стилистика — повторы слов рядом (тавтологии) и слишком длинные "
            "предложения. Только отчёт, файлы не меняются.\n"
            "• Статистика — объём, средняя длина предложения, доля диалогов, "
            "слова-паразиты; умеет вести CSV-дневник объёма.\n"
            "• Ё/Е-аудит — спорные места с ё: имена из реестра, словарные пары, "
            "омографы (все/всё). Замена — выборочно в витрине.\n"
            "• Типографика — «ёлочки», тире, многоточия, пунктуация и неразрывные "
            "пробелы; вычитка показывает проблемные места по строкам (для Word — "
            "по абзацам).\n"
            "• Экспорт в Word — глава .md превращается в .docx для беты и "
            "редактора.\n"
            "• Эхо-фразы — одинаковые зачины и конструкции, повторяющиеся "
            "между главами.\n"
            "Форматы: подпись у каждой карточки говорит, что она читает. "
            "(Word) — .docx читается и правится; «только заметки» — "
            "только .md/.txt, Word не трогается.\n"
            "Безопасность: по умолчанию всё только читает и пишет отчёт. "
            "Реальная запись — по галочке, с бэкапом (.bak рядом с файлом)."))

        # --- 1. АНТИРЕШИМОСТЬ (05.11: переехала из «Чистки») ---
        s1 = Section(parent,
                     "1. АНТИРЕШИМОСТЬ — запрещённая лексика и пафос",
                     subtitle="форматы: .txt, .md, .docx (Word)")
        self.f_ar = PathField(s1.inner, "Папка или файл:", "ar_input", CFG,
                              file_mode="both",
                              tooltip="Папка (обход рекурсивный) или один файл "
                                      ".md/.txt/.docx.")
        self.c_ar_fix = CheckField(s1.inner, "Зачистить (вырезать hard)",
                                   "ar_clean", CFG, default=False,
                                   tooltip="Без галочки — только поиск, лог и "
                                           "отчёт. С галочкой — вырезает жёсткие "
                                           "вхождения (решимость, лозунги, "
                                           "превозмогание…), создавая .bak рядом "
                                           "с файлом. soft-слова (надежда, "
                                           "штампы) только подсвечиваются — "
                                           "решает автор.")
        self.c_ar_fix.pack(anchor="w")
        ctk.CTkLabel(s1.inner, justify="left", anchor="w", font=FONT_SMALL,
                     wraplength=500, text=(
            "Словари: data/resolve_db.yaml (лексика памятки) и "
            "data/pathos_db.yaml (антипафос) — правятся вручную. Находки с "
            "подсказками («Она смотрела в одну точку. Не мигала») дописываются "
            "в лог reports/antiresolve.log. Эмоции — через действие."
        )).pack(anchor="w", pady=(0, 2))
        row1 = button_row(s1.inner)
        b_ar = ActionButton(
            row1, "Запустить АНТИРЕШИМОСТЬ", self._run_ar,
            kind="safe", width=235,
            tooltip="Поиск запрещённой лексики и пафоса. С галочкой "
                    "«Зачистить» — правка с .bak.")
        b_ar.pack(side="left")
        b_ar.link_danger(self.c_ar_fix.var)

        # --- 2. штампы ИИ-текста и канцелярит (переехали из «Хранилища») ---
        s2 = Section(parent, "2. Штампы ИИ-текста и канцелярит",
                     subtitle="форматы: .md, .txt, .docx (Word)")
        self.f_pc = PathField(s2.inner, "Папка или файл:", "pc_input", CFG,
                              file_mode="both",
                              tooltip="Папка с текстами (.md/.txt/.docx) или один файл. "
                                      "Обход рекурсивный.")
        self.f_pc_custom = EntryField(s2.inner, "Свой словарь (yaml):", "pc_custom", CFG,
                                      placeholder="необязательно",
                                      tooltip="YAML-файл со списком своих фраз. "
                                              "Пусто = встроенный словарь (~60 штампов).")
        self.f_pc_phrase = EntryField(s2.inner, "Своя фраза:", "pc_phrase", CFG,
                                      placeholder="необязательно",
                                      tooltip="Фраза для разового поиска (регистр не важен).")
        self.c_pc_add = CheckField(s2.inner, "Запомнить фразу в словарь", "pc_add", CFG,
                                   default=False,
                                   tooltip="Добавит фразу в phrases.yaml — она будет "
                                           "искаться всегда.")
        self.c_pc_add.pack(anchor="w")
        btns_pc = button_row(s2.inner, pady=(6, 0))
        ActionButton(btns_pc, "Найти штампы", self._run_phrase_check,
                     kind="safe", width=160,
                     tooltip="Ищет шаблонные нейросетевые обороты и канцелярит "
                             "по всем .md/.txt/.docx. Только отчёт, ничего "
                             "не изменяет.").pack(side="left", padx=(0, 8))
        self.c_pc_dry = CheckField(btns_pc, "Только отчёт (не менять)", "pc_dry", CFG,
                                   default=True,
                                   tooltip="ВКЛ — показывается план замен без правки файлов. "
                                           "ВЫКЛ — реальные замены (с бэкапом).")
        self.c_pc_dry.pack(side="left", padx=(0, 12))
        b_pc_clean = ActionButton(
            btns_pc, "Почистить штампы", self._run_phrase_clean,
            kind="primary", width=190,
            tooltip="Удаляет/заменяет штампы по словарю очистки "
                    "(phrases_clean.yaml можно дополнить своими правилами). "
                    "Например: «в современном мире» -> «сегодня», "
                    "«стоит отметить, что» -> удалить. С бэкапом.")
        b_pc_clean.pack(side="left", padx=(0, 8))
        b_pc_clean.link_danger(self.c_pc_dry.var, invert=True)
        # 08.11: ряд делился надвое — при масштабе 1.25 не влезал в 900px
        btns_pc2 = button_row(s2.inner, pady=(4, 0))
        self.c_pc_review = CheckField(btns_pc2, "Выборочно (витрина)",
                                      "pc_review", CFG, default=False,
                                      tooltip="Показать каждое вхождение "
                                              "с контекстом и выбрать, что "
                                              "чистить. Работает с кнопкой "
                                              "«Почистить штампы».")
        self.c_pc_review.pack(side="left")

        # --- 3. стилистика (переехала из «Хранилища») ---
        s3 = Section(parent, "3. Стилистика: повторы рядом и длинные предложения",
                     subtitle="форматы: .md, .txt, .docx (Word)")
        self.f_style = PathField(s3.inner, "Папка или файл:", "style_input", CFG,
                                 file_mode="both",
                                 tooltip="Папка с текстами (.md/.txt/.docx) или "
                                         "один файл. Только чтение, файлы "
                                         "не изменяются.")
        self.f_style_reg = EntryField(s3.inner, "Реестр персонажей (yaml):",
                                      "style_registry", CFG,
                                      placeholder="необязательно",
                                      tooltip="Формы имён из реестра "
                                              "не будут считаться повторами.")
        r3 = ctk.CTkFrame(s3.inner, fg_color="transparent")
        r3.pack(fill="x", pady=2)
        self.e_style_window = EntryField(r3, "Окно повтора (слов):",
                                         "style_window", CFG, placeholder="5",
                                         width_label=150,
                                         tooltip="Слово считается повтором, "
                                                 "если встретилось второй раз "
                                                 "в пределах этого числа слов.")
        self.e_style_window.pack(side="left", padx=(0, 12))
        self.e_style_long = EntryField(r3, "Длинное предложение (слов):",
                                       "style_long", CFG, placeholder="25",
                                       width_label=190,
                                       tooltip="Предложения длиннее этого числа "
                                               "слов попадают в отчёт.")
        self.e_style_long.pack(side="left", padx=0)
        row3 = button_row(s3.inner)
        ActionButton(row3, "Построить стилистический отчёт", self._run_style,
                     kind="safe", width=260,
                     tooltip="Повторы слов в пределах окна (тавтологии, кроме "
                             "служебных и форм имён) и слишком длинные "
                             "предложения. Файлы не изменяются."
                     ).pack(side="left")

        # --- 4. статистика текста (переехала из «Хранилища») ---
        s4 = Section(parent, "4. Статистика текста (объём, диалоги, паразиты)",
                     subtitle="форматы: .md, .txt, .docx (Word)")
        self.f_stats = PathField(s4.inner, "Папка или файл:", "stats_input", CFG,
                                 file_mode="both",
                                 tooltip="Папка с текстами (.md/.txt/.docx) или "
                                         "один файл. Только чтение.")
        self.c_stats_csv = CheckField(s4.inner, "Дописывать в CSV-дневник",
                                      "stats_csv", CFG, default=False,
                                      tooltip="Каждый запуск добавляет строку "
                                              "«дата; файл; слова; …» в "
                                              "reports/stats_log.csv — удобно "
                                              "следить за прогрессом в Excel.")
        self.c_stats_csv.pack(anchor="w")
        row4 = button_row(s4.inner)
        ActionButton(row4, "Построить статистику", self._run_stats,
                     kind="safe", width=235,
                     tooltip="Объём, средняя длина предложения, доля диалогов, "
                             "частотные слова-паразиты на 1000 слов."
                     ).pack(side="left")

        # --- 5. ё/е-аудит (переехал из «Имён персонажей») ---
        s5 = Section(parent, "5. Ё/Е-аудит",
                     subtitle="форматы: .txt, .md, .docx (Word)")
        self.f_yo_input = PathField(s5.inner, "Тексты (папка/файл):", "yo_input",
                                    CFG, file_mode="both",
                                    tooltip="Папка или файл .md/.txt/.docx. "
                                            "В docx правки применяются пословно "
                                            "по отмеченным формам во всём "
                                            "документе (строки витрины там "
                                            "условны).")
        self.f_yo_reg = PathField(s5.inner, "Реестр (yaml):", "yo_registry", CFG,
                                  file_mode="file",
                                  tooltip="Реестр персонажей: имена с ё (Семён) "
                                          "сверяются с написанием в тексте (Семен).")
        row5 = button_row(s5.inner)
        # 07.11: submenu=True — синяя кнопка со стрелкой «▸»: открывает
        # витрину со списком вхождений, а не запускает операцию в журнал
        ActionButton(row5, "Ё/Е-аудит (витрина)", self._run_yo,
                     submenu=True, width=235,
                     tooltip="Собирает спорные места: имена из реестра, словарные "
                             "пары и омографы (все/всё). Замена — только по "
                             "выбранным вхождением в диалоге."
                     ).pack(side="left")

        # --- 6. типографика (07.11: переехала из «Чистки», добавлена вычитка) ---
        s_typo = Section(parent, "6. Типографика: «ёлочки», тире, пунктуация",
                         subtitle="форматы: .md, .txt, .docx (Word)")
        self.f_typo = PathField(s_typo.inner, "Папка или файл:", "typo_input", CFG,
                                file_mode="both",
                                tooltip="Папка (обход рекурсивный) или один файл "
                                        ".md/.txt/.docx.")
        r_typo = ctk.CTkFrame(s_typo.inner, fg_color="transparent")
        r_typo.pack(fill="x", pady=4)
        self.c_typo_fix = CheckField(r_typo, "Применить изменения", "typo_fix", CFG,
                                     default=False,
                                     tooltip="Без галочки — dry-run (только отчёт). "
                                             "С галочкой — реально правит, "
                                             "создавая .bak рядом с файлом.")
        self.c_typo_fix.pack(side="left", padx=(0, 16))
        self.c_typo_nbsp = CheckField(r_typo, "Неразрывные пробелы", "typo_nbsp", CFG,
                                      default=False,
                                      tooltip="Неразрывный пробел: предлоги/союзы "
                                              "(в, и, с, на…), «№», перед тире; "
                                              "инициалы «И. И. Иванов»; «т. д.», «и др.»; "
                                              "число не отрывается от слова "
                                              "(«10 лет», «1812 г.»).")
        self.c_typo_nbsp.pack(side="left", padx=16)
        ctk.CTkLabel(s_typo.inner, justify="left", anchor="w", font=FONT_SMALL,
                        wraplength=500, text=(
            "Кавычки \"...\" и „лапки“ → «ёлочки», 3+ точки → …, «?...» → «?..», "
            "«слово - слово» → «слово — слово», диапазон лет «1941-1945» → "
            "«1941—1945», «- Реплика» → «— Реплика» (txt/docx). Пунктуация: "
            "«Да,нет» → «Да, нет», «слово ,» → «слово,», «А.С.Пушкин» → "
            "«А. С. Пушкин», двойные пробелы сжимаются. Код-блоки, frontmatter и "
            "inline-код не трогаются. Вычитка — только список проблем, файлы "
            "не меняет."
        )).pack(anchor="w", pady=(0, 2))
        row_typo = button_row(s_typo.inner)
        b_typo_check = ActionButton(
            row_typo, "Вычитка: найти проблемы", self._run_typo_check,
            kind="safe", width=225,
            tooltip="Список проблем с адресами (файл:строка, для Word — абзац): "
                    "прямые кавычки, ёлочки без пары, дефис вместо тире, "
                    "двойные пробелы, «?...» вместо «?..» и другое. Файлы "
                    "не изменяются.")
        b_typo_check.pack(side="left", padx=(0, 8))
        b_typo = ActionButton(
            row_typo, "Запустить типографику", self._run_typo,
            kind="safe", width=235,
            tooltip="«Ёлочки», тире, многоточия, пунктуация, неразрывные пробелы "
                    "(опция). Dry-run по умолчанию.")
        b_typo.pack(side="left")
        b_typo.link_danger(self.c_typo_fix.var)

        # --- 7. экспорт в Word (06.11: BACKLOG №4 добрался до GUI) ---
        s6 = Section(parent, "7. Экспорт в Word",
                     subtitle="форматы: .md/.markdown → .docx")
        self.f_export_in = PathField(s6.inner, "Откуда (.md):", "export_input", CFG,
                                     file_mode="both",
                                     tooltip="Глава или папка с главами "
                                             ".md/.markdown. Папка: каждый .md "
                                             "→ одноимённый .docx, вложенные "
                                             "папки воспроизводятся.")
        self.f_export_out = PathField(s6.inner, "Куда (.docx):", "export_output", CFG,
                                      file_mode="both",
                                      tooltip="Файл .docx (для одной главы) или "
                                              "папка приёмник (для папки глав).")
        self.c_export_force = CheckField(
            s6.inner, "Перезаписывать существующие .docx", "export_force",
            CFG, default=False,
            tooltip="Без галочки существующий .docx не затирается — экспорт "
                    "молча терять главы нельзя. С галочкой — перезапись "
                    "всегда.")
        self.c_export_force.pack(anchor="w")
        row6 = button_row(s6.inner)
        ActionButton(row6, "Экспорт в Word", self._run_export,
                     kind="primary", width=180,
                     tooltip="Собирает .docx: заголовки, списки, курсив. Пишет "
                             "новые файлы — существующие только с галочкой "
                             "перезаписи.").pack(side="left")

        # --- 8. эхо-фразы (06.11: BACKLOG №6 добрался до GUI) ---
        s7 = Section(parent, "8. Эхо-фразы — повторы конструкций между главами",
                     subtitle="форматы: .md, .txt, .docx (Word)")
        self.f_echo = PathField(s7.inner, "Главы (папка/файл):", "echo_input", CFG,
                                file_mode="both",
                                tooltip="Главы .md/.txt/.docx или папка. Эхо — "
                                        "это повтор между РАЗНЫМИ файлами, "
                                        "внутри одного файла ищет «Стилистика».")
        # 06.11: параметры поиска были только в CLI — теперь и здесь,
        # значения запоминаются между запусками
        r7p = ctk.CTkFrame(s7.inner, fg_color="transparent")
        r7p.pack(fill="x", pady=2)
        self.e_echo_n = EntryField(r7p, "Слов во фразе:", "echo_n", CFG,
                                   placeholder="3", width_label=110,
                                   tooltip="Длина n-граммы: сколько слов должны "
                                           "повторяться подряд. По умолчанию 3.")
        self.e_echo_n.pack(side="left", padx=(0, 12))
        self.e_echo_n.entry.configure(width=64)
        self.e_echo_min = EntryField(r7p, "Мин. глав:", "echo_min_files", CFG,
                                     placeholder="2", width_label=80,
                                     tooltip="Фраза попадает в отчёт, если встретилась "
                                             "минимум в этом числе РАЗНЫХ файлов. "
                                             "По умолчанию 2.")
        self.e_echo_min.pack(side="left", padx=(0, 12))
        self.e_echo_min.entry.configure(width=64)
        self.e_echo_top = EntryField(r7p, "В топ:", "echo_top", CFG,
                                     placeholder="25", width_label=52,
                                     tooltip="Сколько самых частых эхо показывать "
                                             "в отчёте. По умолчанию 25.")
        self.e_echo_top.pack(side="left")
        self.e_echo_top.entry.configure(width=64)
        row7 = button_row(s7.inner)
        ActionButton(row7, "Найти эхо-фразы", self._run_echo,
                     kind="safe", width=200,
                     tooltip="N-граммы (по умолчанию 3 слова), встретившиеся в "
                             "двух и более главах: «мир сжался», «задышал "
                             "ровнее». Топ-25 в отчёте. Файлы не меняются."
                     ).pack(side="left")

    def _run_typo(self):
        # 07.11: типографика переехала из «Чистки» (ключи конфига не менялись,
        # история путей переносится), добавлен режим вычитки
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

    def _run_typo_check(self):
        # 07.11: вычитка — список проблем с адресами, файлы не правятся
        from gui_ctk import run_internal
        p = self.f_typo.get()
        if not p:
            self._log("Укажите папку или файл.\n")
            return
        self._log("Вычитка: ищу проблемные места (файл:строка)...\n")
        run_internal("typography", ["--input", p, "--check"])

    def _run_export(self):
        # 06.11: экспорт главы .md → .docx (движок BACKLOG №4, до этого
        # был только в CLI)
        from gui_ctk import run_internal
        src = self.f_export_in.get()
        dst = self.f_export_out.get()
        if not src or not dst:
            self._log("Укажите, откуда брать .md и куда класть .docx.\n")
            return
        args = ["--input", src, "--out", dst]
        if self.c_export_force.get():
            args.append("--force")
        self._log(f"Экспорт в Word: {src} → {dst}\n")
        run_internal("export_docx", args)

    def _run_echo(self):
        # 06.11: параметры поиска вынесены в карточку (echo_n,
        # echo_min_files, echo_top) — раньше только в командной строке
        from gui_ctk import run_internal
        if not self.f_echo.get():
            self._log("Укажите папку или файл для поиска эхо-фраз.\n")
            return
        args = ["--input", self.f_echo.get()]
        for field, flag, label in (
                (self.e_echo_n, "--n", "Слов во фразе"),
                (self.e_echo_min, "--min-files", "Мин. глав"),
                (self.e_echo_top, "--top", "В топ")):
            v = field.get().strip()
            if v and not v.isdigit():
                self._log(f"Эхо-фразы, «{label}»: введите целое число.\n",
                          "warn")
                return
            if v:
                args += [flag, v]
        self._log("Ищу эхо-фразы — повторы между главами...\n")
        run_internal("echo_finder", args)

    def _log(self, msg, tag=None):
        from gui_ctk import _app
        _app.log_line(msg, tag)

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

    def _run_phrase_check(self):
        # 22.09: phrase_check — штампы ИИ-текста и канцелярит
        from gui_ctk import run_cmd
        p = self.f_pc.get()
        if not p:
            self._log("Укажите папку или файл для поиска штампов.\n")
            return
        phrase = self.f_pc_phrase.get()
        custom = self.f_pc_custom.get()
        # 22.09: «запомнить» — добавляем фразу в постоянный словарь.
        # 24.10: делаем это до поиска и в главном потоке: лог не пишется
        # из чужого потока (Tk так нельзя).
        # 04.11: запись словаря идёт прямо в процессе — раньше запускался
        # отдельный процесс с таймаутом 30 с, и всё это время окно
        # не отвечало.
        if phrase and self.c_pc_add.get():
            import io
            from contextlib import redirect_stdout
            from tools import phrase_check
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    phrase_check.add_phrase(phrase)
                self._log(buf.getvalue() or "Фраза учтена в словаре.\n")
            except Exception as e:
                self._log(f"Не удалось запомнить фразу: {e}\n", "warn")
        from gui_ctk import tool_cmd
        cmd = tool_cmd("phrase_check", "--input", p)
        if custom:
            cmd += ["--custom", custom]
        if phrase:
            cmd += ["--phrase", phrase]
        # 22.09: сразу пишем в лог, что поиск запущен (скан с docx идёт долго,
        # без строки пользователь не понимает, работает кнопка или нет)
        self._log(f"Ищу штампы в {p} — прогресс внизу над логом...\n")
        run_cmd(cmd)

    def _run_phrase_clean(self):
        # 22.09: чистка штампов по словарю замен (dry-run по умолчанию)
        # 01.10: «Выборочно (витрина)» — сначала обзор вхождений в диалоге
        from gui_ctk import run_cmd, _app
        p = self.f_pc.get()
        if not p:
            _app.log_line("Укажите папку или файл для чистки штампов.\n")
            return
        if self.c_pc_review.get():
            self._run_review(p)
            return
        dry = self.c_pc_dry.get()
        from gui_ctk import tool_cmd
        cmd = tool_cmd("phrase_check", "--input", p, "--clean")
        if dry:
            cmd += ["--dry-run"]
        else:
            cmd += ["--yes"]
        _app.log_line(
            f"{'План чистки (dry-run)' if dry else 'ЧИСТКА (реальная замена)'}: "
            f"{p} — прогресс внизу над логом...\n")
        run_cmd(cmd)

    def _run_style(self):
        # 03.10: стилистический отчёт — повторы рядом + длинные предложения
        from gui_ctk import run_internal
        p = self.f_style.get()
        if not p:
            self._log("Укажите папку или файл.\n")
            return
        win = self.e_style_window.get()
        long = self.e_style_long.get()
        if win and not win.isdigit():
            self._log("«Окно повтора»: введите целое число.\n", "warn")
            return
        if long and not long.isdigit():
            self._log("«Длинное предложение»: введите целое число.\n", "warn")
            return
        args = ["--input", p]
        reg = self.f_style_reg.get()
        if reg:
            args += ["--registry", reg]
        if win:
            args += ["--window", win]
        if long:
            args += ["--long", long]
        run_internal("style_report", args)

    def _run_stats(self):
        from gui_ctk import run_internal
        if not self.f_stats.get():
            self._log("Укажите папку или файл.\n")
            return
        args = ["--input", self.f_stats.get()]
        # 03.10: CSV-дневник объёма (reports/stats_log.csv)
        if self.c_stats_csv.get():
            args.append("--csv")
        run_internal("text_stats", args)

    def _run_review(self, path):
        # 01.10: витрина — subprocess собирает вхождения, диалог даёт выбрать.
        # Поток кладёт результат в очередь, главный поток опрашивает через
        # after() (звать after из чужого потока нельзя: main thread is not
        # in main loop). 24.10: задача идёт через общий «занято», «Стоп»
        # умеет завершить процесс.
        import queue as _queue
        import subprocess
        import threading
        from gui_ctk import _app as app, CREATE_FLAGS

        if not app.begin_background("Витрина штампов"):
            return
        from gui_ctk import tool_cmd
        q = _queue.Queue()

        def _worker():
            # 20.10: любой сбой (таймаут, нет интерпретатора) кладёт в
            # очередь маркер — раньше полл после ошибки крутился вечно
            proc = None
            # 04.11: таймаут витрины — настройка review_timeout_min (1–60)
            from gui_ctk import _cfg_int
            timeout_s = _cfg_int("review_timeout_min", 10, 1, 60) * 60
            try:
                proc = subprocess.Popen(
                    tool_cmd("phrase_check", "--input", path, "--review"),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    creationflags=CREATE_FLAGS)
                app._bg_proc = proc
                # 04.11: «Стоп» мог сработать между запуском и присвоением —
                # теперь такой процесс всё равно будет остановлен
                if not app._bg_active:
                    proc.terminate()
                out, _ = proc.communicate(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                    # 04.11: дожидаемся — иначе незакрытые пайпы и
                    # дескриптор процесса до сборщика мусора
                    proc.wait(timeout=5)
                except Exception:
                    pass
                q.put(("err", f"Витрина не успела за {timeout_s // 60} мин "
                              "и была остановлена.\n"))
                return
            except Exception as e:
                q.put(("err", f"Витрина не запустилась: {e}\n"))
                return
            finally:
                app._bg_proc = None
            hits = []
            for line in (out or "").splitlines():
                if line.startswith("REVIEW\t"):
                    parts = line.split("\t", 5)
                    if len(parts) == 6:
                        hits.append((parts[1], parts[2], parts[3],
                                     parts[4], parts[5]))
            q.put(("ok", hits))

        def _check():
            from gui_ctk import _app as app2
            try:
                kind, payload = q.get_nowait()
            except _queue.Empty:
                app2.after(150, _check)
                return
            try:
                from gui_ctk import STOP_FILE
                if STOP_FILE.exists():
                    self._log("Витрина остановлена.\n", "warn")
                    return
                if kind == "err":
                    self._log(payload, "err")
                    return
                self._open_review(payload)
            finally:
                app2.finish_background()

        try:
            threading.Thread(target=_worker, daemon=True).start()
        except Exception as e:
            self._log(f"Витрина не запустилась: {e}\n", "err")
            app.finish_background()
            return
        app.after(150, _check)
        self._log("Витрина: собираю вхождения штампов...\n")

    def _open_review(self, hits):
        from gui_ctk import _app
        if not hits:
            _app.log_line("Штампов не найдено — витрина пуста.\n", "ok")
            return
        _app.log_line(f"Витрина: {len(hits)} вхождений.\n")

        def _apply(pairs):
            from tools import phrase_check
            out = []
            for msg in phrase_check.clean_selection(pairs):
                out.append((msg + "\n",
                            "ok" if msg.startswith("[ОЧИЩЕН]") else None))
            return out

        import review_dialog
        review_dialog.show(_app, hits, _apply)

    def _run_yo(self):
        # 20.10: ё/е-аудит — спорные места с ё и е в отдельной витрине
        import io
        import queue as _queue
        import sys
        import threading
        from gui_ctk import _app

        p = self.f_yo_input.get()
        if not p:
            self._log("Укажите папку или файл для Ё/Е-аудита.\n")
            return
        if not _app.begin_background("Ё/Е-аудит"):
            return
        reg = self.f_yo_reg.get() or None
        q = _queue.Queue()

        def _worker():
            # 04.11: подмена stdout живёт только до конца задачи —
            # раньше брошенный StringIO оставался до конца процесса
            _stdout_keep = sys.stdout
            if _stdout_keep is None:
                sys.stdout = io.StringIO()  # pythonw: print движков в никуда
            try:
                from tools import yo_audit
                dictionary = yo_audit.load_dict()
                name_p = []
                if reg:
                    from core import name_registry as nr
                    name_p = yo_audit.name_pairs(nr.load_registry(reg))
                targets = yo_audit.yowords_all(dictionary, name_p)
                hits = []
                stats = {"ё_всего": 0}
                stopped = False
                for f in yo_audit.iter_text_files(p):
                    if yo_audit.stop_requested():
                        stopped = True
                        break
                    hits.extend(yo_audit.scan(f, targets, stats))
                if stopped:
                    q.put(("stopped", None, None))
                    return
                # 05.11: docx-находки больше не вырезаются — правка docx
                # реализована в yo_audit.clean_selection (пословно по всем
                # отмеченным формам документа); фильтр оставлял Word-главы
                # невидимыми для витрины
                q.put(("ok", hits, targets))
            except Exception as e:
                q.put(("err", f"Ё/Е-аудит не удался: {e}", None))
            finally:
                sys.stdout = _stdout_keep

        def _check():
            from gui_ctk import _app as app
            try:
                kind, payload, targets = q.get_nowait()
            except _queue.Empty:
                app.after(150, _check)
                return
            try:
                if kind == "stopped":
                    self._log("Ё/Е-аудит остановлен.\n", "warn")
                    return
                if kind == "err":
                    self._log(payload + "\n", "err")
                    return
                self._open_yo(payload, targets)
            finally:
                app.finish_background()

        try:
            threading.Thread(target=_worker, daemon=True).start()
        except Exception as e:
            self._log(f"Ё/Е-аудит не запустился: {e}\n", "err")
            _app.finish_background()
            return
        _app.after(150, _check)
        self._log("Ё/Е-аудит: собираю спорные места...\n")

    def _open_yo(self, hits, _targets):
        from gui_ctk import _app
        if not hits:
            _app.log_line("Ё/Е-аудит: спорных мест не найдено.\n", "ok")
            return
        _app.log_line(f"Ё/Е-аудит: {len(hits)} вхождений.\n")

        # написание как в тексте -> правильная форма (для кнопки применить)
        wrong_to_right = {}
        for w, r, _fs, _ln, _frag in hits:
            wrong_to_right.setdefault(w.lower(), r)

        def _apply(pairs):
            from tools import yo_audit
            # 04.11: витрина передаёт (слово, файл, строка) — правятся
            # только отмеченные вхождения, а не все в файле
            by_file = {}
            for w, fs, ln in pairs:
                by_file.setdefault(fs, []).append(
                    (w, wrong_to_right.get(w.lower(), ""), ln))
            out = []
            for msg in yo_audit.clean_selection(by_file):
                out.append((msg + "\n",
                            "ok" if msg.startswith("[Ё]") else None))
            return out

        import review_dialog
        review_dialog.show(_app, hits, _apply)
