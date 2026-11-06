"""Вкладка «Имена»: registry-builder + consistency + объяснение реестра.
18.09: переделана на CustomTkinter (widgets_ctk).
05.11: Ё/Е-аудит переехал во вкладку «Писателям» (tabs_writers)."""
import customtkinter as ctk

from gui_config import CFG
from widgets_ctk import (PathField, EntryField, CheckField, HelpBox,
                         Section, Tooltip, FONT_SMALL, FONT_MONO,
                         ActionButton, button_row)


class NamesTab(ctk.CTkFrame):
    LABEL = "Имена персонажей"

    def _build(self, parent):
        self.parent = parent
        HelpBox(parent, text=(
            "Как это работает:\n"
            "1) Registry-builder сканирует ваши тексты и находит повторяющиеся "
            "слова-кандидаты — это могут быть имена персонажей.\n"
            "2) Вы смотрите список, оставляете нужные и сохраняете их в «реестр» — "
            "это простой YAML-файл со списком имён (кто текущее имя, кто старые варианты).\n"
            "3) Consistency проверяет тексты по реестру: находит старые имена, "
            "опечатки и опасные формы (например, падежи старого имени)."))

        # --- Что такое реестр ---
        s0 = Section(parent, "Реестр (YAML) — что это",
                     subtitle="форматы: .yaml (реестр)")
        Tooltip(s0, "Реестр — обычный текстовый файл .yaml со списком персонажей. "
                    "Его создаёт registry-builder (кнопка ниже), а вы потом "
                    "редактируете вручную в блокноте.")
        ctk.CTkLabel(s0.inner, justify="left", font=FONT_MONO,
                     anchor="w", text=(
            '- имя: Лина\n'
            '  формы: [Лина, Лины, Лине, Лину, Линой]   # все варианты имени\n'
            '  старое: [Линна]               # как звали раньше\n'
            '  старое_опасное: [Лине]        # совпадает с формой другого имени\n'
            '  опечатки: [Лима]\n'
            '- имя: Эрика\n'
            '  формы: [Эрика, Эрике]\n'
            '  старое: []\n'
            "\n"
            "Consistency читает этот файл и проверяет: нет ли в текстах\n"
            "старых имён и опечаток из реестра."
        )).pack(anchor="w")

        # --- Шаг 1: registry-builder ---
        s1 = Section(parent, "Шаг 1 — найти имена-кандидаты (registry-builder)",
                     subtitle="форматы: .md, .txt, .docx (Word)")
        self.f_input = PathField(s1.inner, "Тексты (папка):", "names_input", CFG,
                                 file_mode="both",
                                 tooltip="Папка или файл .md/.txt/.docx, где искать имена.")
        self.f_registry = PathField(s1.inner, "Реестр (yaml):", "names_registry", CFG,
                                    file_mode="file",
                                    tooltip="Существующий реестр — его имена будут "
                                            "исключены из кандидатов. Можно не указывать.")
        self.f_out = PathField(s1.inner, "Сохранить в:", "names_out", CFG,
                               file_mode="file",
                               tooltip="Куда записать найденных кандидатов (yaml). "
                                       "Пусто = только показать в окне.")
        r = ctk.CTkFrame(s1.inner, fg_color="transparent")
        r.pack(fill="x", pady=4)
        ctk.CTkLabel(r, text="Мин. упоминаний:", font=FONT_SMALL).pack(side="left")
        self.min_count = EntryField(r, "", "names_min_count", CFG, width_label=0)
        self.min_count.pack(side="left", padx=4)
        self.min_count.entry.configure(width=70)
        Tooltip(self.min_count.entry, "Слова, встречающиеся реже этого числа, не показываются. "
                                "Для больших текстов ставьте 5–10, чтобы отсечь "
                                "техно-лексикон (bass, serum, cyberpunk и т.п.).")
        ctk.CTkLabel(r, text="5–10 для больших текстов — меньше мусора",
                     font=FONT_SMALL).pack(side="left", padx=8)

        row1 = button_row(s1.inner)
        ActionButton(row1, "Найти кандидатов", self._run_builder,
                     kind="safe", width=235,
                     tooltip="Сканирует тексты и показывает слова-кандидаты "
                             "в имена.").pack(side="left")

        # --- Шаг 2: consistency ---
        s2 = Section(parent, "Шаг 2 — проверить тексты по реестру (consistency)",
                     subtitle="форматы: .md, .txt, .docx (Word)")
        self.f_cons_input = PathField(s2.inner, "Тексты (папка):", "cons_input", CFG,
                                      file_mode="both",
                                      tooltip="Папка или файл (.md/.txt/.docx), где проверять имена.")
        self.f_cons_reg = PathField(s2.inner, "Реестр (yaml):", "cons_registry", CFG,
                                    file_mode="file",
                                    tooltip="Файл реестра со списком персонажей "
                                            "(см. пример выше).")
        row2 = button_row(s2.inner)
        ActionButton(row2, "Проверить имена", self._run_consistency,
                     kind="safe", width=235,
                     tooltip="Проверяет тексты по реестру: старые имена, опечатки. "
                             "Падежные формы находятся автоматически (pymorphy3)."
                     ).pack(side="left")

        # --- Шаг 3: матрица упоминаний (01.10) ---
        s3 = Section(parent, "Шаг 3 — матрица упоминаний (кто где встречается)",
                     subtitle="форматы: .md, .txt, .docx (Word)")
        self.f_mat_input = PathField(s3.inner, "Тексты (папка):", "mat_input", CFG,
                                     file_mode="both",
                                     tooltip="Папка или файл, где считать упоминания.")
        self.f_mat_reg = PathField(s3.inner, "Реестр (yaml):", "mat_registry", CFG,
                                   file_mode="file",
                                   tooltip="Реестр персонажей (тот же, что в шаге 2).")
        row3 = button_row(s3.inner)
        ActionButton(row3, "Построить матрицу", self._run_matrix,
                     kind="safe", width=235,
                     tooltip="Таблица «персонаж × файл»: где и сколько раз "
                             "упоминается каждый персонаж (включая падежи)."
                     ).pack(side="left")

        # --- Падежные формы реестра (01.10) ---
        s4 = Section(parent, "Падежные формы реестра (pymorphy3)",
                     subtitle="форматы: .yaml (реестр)")
        ctk.CTkLabel(s4.inner, justify="left", anchor="w", font=FONT_SMALL,
                     text="Показывает, каких падежных форм не хватает в реестре. "
                          "Дописывает по кнопке ниже, с .bak-бэкапом."
                     ).pack(anchor="w")
        self.f_forms_fill = CheckField(s4.inner, "Дописать в реестр",
                                       "forms_fill", CFG, default=False,
                                       tooltip="Не только показать, но и дописать "
                                               "формы в YAML (с .bak).")
        self.f_forms_fill.pack(anchor="w")
        row4 = button_row(s4.inner)
        b_forms = ActionButton(
            row4, "Показать недостающие падежи", self._run_forms,
            kind="safe", width=260,
            tooltip="Сравнивает реестр с формами pymorphy3 и выводит "
                    "недостающие (тот же реестр, что в шаге 2).")
        b_forms.pack(side="left")
        b_forms.link_danger(self.f_forms_fill.var)

        # --- Кандидаты -> реестр (01.10) ---
        s5 = Section(parent, "Кандидаты -> реестр (без ручного копирования)",
                     subtitle="форматы: .yaml (реестр)")
        self.f_merge_cand = PathField(s5.inner, "Кандидаты (yaml):", "merge_candidates",
                                      CFG, file_mode="file",
                                      tooltip="Файл кандидатов, который создал "
                                              "registry-builder (поле «Сохранить в» выше).")
        self.f_merge_reg = PathField(s5.inner, "Реестр (yaml):", "merge_registry", CFG,
                                     file_mode="file",
                                     tooltip="Ваш основной реестр персонажей. "
                                             "Существующие имена не дублируются.")
        self.f_merge_names = EntryField(s5.inner, "Имена (через запятую):",
                                        "merge_names", CFG,
                                        placeholder="все",
                                        tooltip="Пусто = добавить всех кандидатов. "
                                                "Или перечислите нужные: Эрика, Кайдзо.")
        self.c_merge_add = CheckField(s5.inner, "Применить (дописать в реестр)",
                                      "merge_add", CFG, default=False,
                                      tooltip="Без галочки — только отчёт. "
                                              "С галочкой — дописывает (с .bak).")
        self.c_merge_add.pack(anchor="w")
        row5 = button_row(s5.inner)
        b_merge = ActionButton(
            row5, "Добавить кандидатов в реестр", self._run_merge_registry,
            kind="safe", width=260,
            tooltip="Сводит кандидатов registry-builder'а с реестром "
                    "и дописывает недостающих персонажей.")
        b_merge.pack(side="left")
        b_merge.link_danger(self.c_merge_add.var)

        # --- MOC-заметки персонажей (01.10) ---
        s6 = Section(parent, "MOC-заметки персонажей (Obsidian)",
                     subtitle="форматы: .md (заметки Obsidian)")
        self.f_moc_input = PathField(s6.inner, "Vault:", "moc_input", CFG,
                                     file_mode="both",
                                     tooltip="Хранилище, где искать упоминания.")
        self.f_moc_reg = PathField(s6.inner, "Реестр (yaml):", "moc_registry", CFG,
                                   file_mode="file",
                                   tooltip="Реестр персонажей.")
        self.f_moc_dir = PathField(s6.inner, "Папка заметок:", "moc_dir", CFG,
                                   file_mode="dir",
                                   tooltip="Например <vault>/Персонажи. Существующие "
                                           "заметки не перезаписываются.")
        self.c_moc_apply = CheckField(s6.inner, "Создать заметки", "moc_apply",
                                      CFG, default=False,
                                      tooltip="Без галочки — только отчёт. "
                                              "С галочкой — создаёт заметки "
                                              "<Имя>.md со ссылками на файлы "
                                              "с упоминаниями.")
        self.c_moc_apply.pack(anchor="w")
        row6 = button_row(s6.inner)
        b_moc = ActionButton(
            row6, "MOC-заметки персонажей", self._run_moc,
            kind="safe", width=235,
            tooltip="Заметка на каждого персонажа: кто где встречается, "
                    "вики-ссылками — Obsidian покажет обратные ссылки.")
        b_moc.pack(side="left")
        b_moc.link_danger(self.c_moc_apply.var)

        # --- список персонажей и проверка имени (07.11) ---
        s7 = Section(parent, "Список персонажей и проверка названий",
                     subtitle="форматы: .md, .txt, .docx (Word), .html")
        self.f_cast = PathField(s7.inner, "Тексты (папка/файл):", "cast_input",
                                CFG, file_mode="both",
                                tooltip="Роман целиком или папка с главами. "
                                        "Инструмент сам собирает все имена "
                                        "с заглавной буквы, без реестра.")
        row7 = button_row(s7.inner)
        ActionButton(row7, "Список персонажей (лог)", self._run_cast,
                     kind="safe", width=235,
                     tooltip="Все имена без повторов + счётчик вхождений + "
                             "пары «Имя Фамилия» + места, где одно имя "
                             "пишется по-разному (Семён/Семен). Лог: "
                             "reports/cast_list.txt."
                     ).pack(side="left")
        self.e_name = EntryField(s7.inner, "Название или имя:", "name_check_input",
                                 CFG, placeholder="например, название корпорации",
                                 tooltip="Проверка придуманного названия на "
                                         "занятость: оффлайн-справочник "
                                         "известных приложений и брендов + "
                                         "советы, где проверить, + готовый "
                                         "дисклеймер для книги.")
        row7b = button_row(s7.inner)
        ActionButton(row7b, "Проверить имя (занятость)", self._run_name_check,
                     kind="safe", width=235,
                     tooltip="Оффлайн-проверка: точные совпадения с известными "
                             "названиями, оценка риска и план проверки "
                             "до печати книги."
                     ).pack(side="left")

        # 05.11: Ё/Е-аудит переехал во вкладку «Писателям» (tabs_writers)

    def _log(self, msg, tag=None):
        from gui_ctk import _app
        _app.log_line(msg, tag)

    def _run_builder(self):
        from gui_ctk import run_internal
        # 22.09: валидация пустого пути
        if not self.f_input.get():
            self._log("Укажите папку текстов.\n")
            return
        # 24.10: порог должен быть целым числом, иначе движок падает
        min_count = self.min_count.get() or "2"
        if not min_count.isdigit() or int(min_count) < 1:
            self._log("Мин. упоминаний: введите целое число 1 или больше.\n",
                      "warn")
            return
        args = ["--input", self.f_input.get(),
                "--min-count", min_count]
        if self.f_out.get():
            args += ["--out", self.f_out.get()]
        if self.f_registry.get():
            args += ["--registry", self.f_registry.get()]
        run_internal("registry_builder", args)

    def _run_consistency(self):
        from gui_ctk import run_internal
        # 22.09: валидация пустых полей до запуска
        if not self.f_cons_input.get():
            self._log("Укажите папку текстов.\n")
            return
        if not self.f_cons_reg.get():
            self._log("Укажите файл реестра (yaml).\n")
            return
        args = ["--input", self.f_cons_input.get(),
                "--registry", self.f_cons_reg.get()]
        run_internal("consistency", args)

    def _run_matrix(self):
        from gui_ctk import run_internal
        if not self.f_mat_input.get():
            self._log("Укажите папку текстов.\n")
            return
        if not self.f_mat_reg.get():
            self._log("Укажите файл реестра (yaml).\n")
            return
        run_internal("character_matrix",
                     ["--input", self.f_mat_input.get(),
                      "--registry", self.f_mat_reg.get()])

    def _run_forms(self):
        from gui_ctk import run_internal
        if not self.f_cons_reg.get():
            self._log("Укажите файл реестра (yaml).\n")
            return
        args = ["--registry", self.f_cons_reg.get()]
        if self.f_forms_fill.get():
            args.append("--fill")
        run_internal("morph_forms", args)

    def _run_merge_registry(self):
        from gui_ctk import run_internal
        if not self.f_merge_cand.get():
            self._log("Укажите файл кандидатов (yaml).\n")
            return
        if not self.f_merge_reg.get():
            self._log("Укажите файл реестра (yaml).\n")
            return
        args = ["--candidates", self.f_merge_cand.get(),
                "--registry", self.f_merge_reg.get()]
        if self.f_merge_names.get():
            args += ["--names", self.f_merge_names.get()]
        if self.c_merge_add.get():
            args.append("--add")
        run_internal("registry_merge", args)

    def _run_moc(self):
        from gui_ctk import run_internal
        if not self.f_moc_input.get():
            self._log("Укажите vault.\n")
            return
        if not self.f_moc_reg.get():
            self._log("Укажите файл реестра (yaml).\n")
            return
        if not self.f_moc_dir.get():
            self._log("Укажите папку для заметок.\n")
            return
        args = ["--input", self.f_moc_input.get(),
                "--registry", self.f_moc_reg.get(),
                "--out-dir", self.f_moc_dir.get()]
        if self.c_moc_apply.get():
            args.append("--apply")
        run_internal("moc_builder", args)
    def _run_cast(self):
        # 07.11: список персонажей без повторов — лог reports/cast_list.txt
        from gui_ctk import run_internal
        if not self.f_cast.get():
            self._log("Укажите папку или файл с текстами.\n")
            return
        self._log("Собираю персонажей...\n")
        run_internal("cast_list", ["--input", self.f_cast.get()])

    def _run_name_check(self):
        # 07.11: проверка придуманного названия на занятость (оффлайн)
        from gui_ctk import run_internal
        name = self.e_name.get().strip()
        if not name:
            self._log("Введите название или имя для проверки.\n")
            return
        self._log(f"Проверяю название «{name}»...\n")
        run_internal("name_check", ["--name", name])
