"""Вкладка «Замены»: md_replace (4 режима), char_search, refile.
18.09: переделана на CustomTkinter (widgets_ctk)."""
import customtkinter as ctk

from gui_config import CFG
from widgets_ctk import (PathField, EntryField, CheckField, HelpBox,
                         Section, BigButton, Tooltip)
from wrappers import (cmd_md_replace, cmd_md_find_bad, cmd_md_fix_encoding,
                      cmd_md_strip_bad, cmd_char_search, cmd_refile)


class ReplaceTab(ctk.CTkFrame):
    LABEL = "Замены"

    def _build(self, parent):
        HelpBox(parent, text=(
            "Как это работает:\n"
            "• Замена текста — массово заменяет текст во всех .md/.txt/.docx файлах хранилища. "
            "Типичный случай: переименовали персонажа — замените старое имя на новое везде. "
            "В docx правится только текст, форматирование сохраняется.\n"
            "• Спецрежимы — диагностика и починка проблемных символов и кодировки "
            "(fix-encoding работает для .md/.txt; docx — это zip, кодировка файла к нему неприменима).\n"
            "• Имена персонажей — проверка по реестру characters.yaml (старые имена, опечатки) "
            "и авто-замена старых на текущие.\n"
            "• Regex по папке — замена по регулярному выражению в любых файлах "
            "(docx подключается только явно: расширение docx в поле «Расширения»).\n"
            "Безопасность: по умолчанию dry-run (покажет, что заменится). "
            "Реальная замена — только с чекбоксом «Применить». Бэкап создаётся "
            "автоматически в md_replace_backups внутри хранилища."))

        # --- 1. замена текста ---
        s1 = Section(parent, "1. Замена текста в .md / .txt / .docx (md_replace)")
        self.f_vault = PathField(s1.inner, "Хранилище (vault):", "md_vault", CFG,
                                 file_mode="both",
                                 tooltip="Папка хранилища (обход по всем .md/.txt/.docx внутри) "
                                         "или один файл.")
        self.f_old = EntryField(s1.inner, "Найти:", "md_old", CFG,
                                tooltip="Текст или регулярное выражение (с галочкой Regex).")
        self.f_new = EntryField(s1.inner, "Заменить на:", "md_new", CFG,
                                tooltip="Новый текст. Пусто = просто удалить найденное.")
        r1 = ctk.CTkFrame(s1.inner, fg_color="transparent")
        r1.pack(fill="x", pady=4)
        self.c_regex = CheckField(r1, "Regex (регулярное выражение)", "md_regex", CFG,
                                  tooltip="Искать по регулярному выражению, например "
                                          r"\d{2}\.\d{2}\.\d{4} — любая дата.")
        self.c_regex.pack(side="left", padx=(0, 16))
        self.c_apply = CheckField(r1, "Применить изменения", "md_apply", CFG,
                                  default=False,
                                  tooltip="Без галочки — dry-run. С галочкой — реально "
                                          "заменяет (бэкап создаётся автоматически).")
        self.c_apply.pack(side="left", padx=16)
        self.c_nobak = CheckField(r1, "Без бэкапа", "md_no_backup", CFG,
                                  default=False,
                                  tooltip="Не создавать бэкап. Не рекомендуется.")
        self.c_nobak.pack(side="left", padx=16)
        BigButton(s1.inner, "Заменить", self._run_md_replace)

        # --- 2. спецрежимы ---
        s2 = Section(parent, "2. Спецрежимы md_replace (диагностика и починка)")
        self.f_vault2 = PathField(s2.inner, "Хранилище (vault):", "md_vault", CFG,
                                  file_mode="both",
                                  tooltip="Тот же vault, что и выше (общее поле). "
                                          "Можно папку или один файл.")
        r2 = ctk.CTkFrame(s2.inner, fg_color="transparent")
        r2.pack(fill="x", pady=4)
        b1 = ctk.CTkButton(r2, text="Найти проблемные символы", height=30,
                           command=self._run_find_bad)
        b1.pack(side="left", padx=(0, 8))
        Tooltip(b1, "Показать все подозрительные unicode-символы в .md файлах "
                    "(битые кавычки, невидимые символы и т.п.). Ничего не меняет.")
        b2 = ctk.CTkButton(r2, text="Починить UTF-8", height=30,
                           command=self._run_fix_encoding)
        b2.pack(side="left", padx=8)
        Tooltip(b2, "Пересохранить файлы в нормальную кодировку UTF-8. "
                    "С «Применить» — реально исправляет, с бэкапом.")
        b3 = ctk.CTkButton(r2, text="Вырезать мусор", height=30,
                           command=self._run_strip_bad)
        b3.pack(side="left", padx=8)
        Tooltip(b3, "Удалить мусорные unicode-символы из .md файлов. "
                    "С «Применить» — реально вырезает, с бэкапом.")
        self.c_spec = CheckField(r2, "Применить", "mdspec_apply", CFG,
                                 default=False,
                                 tooltip="Без галочки — только отчёт. С галочкой — "
                                         "реально исправляет.")
        self.c_spec.pack(side="left", padx=16)

        # --- 3. char_search ---
        s3 = Section(parent, "3. Имена персонажей по реестру (char_search)")
        self.f_cs_vault = PathField(s3.inner, "Хранилище (vault):", "cs_vault", CFG,
                                    file_mode="both",
                                    tooltip="Папка хранилища или один файл "
                                            "(.md/.txt/.docx) для проверки имён.")
        self.f_cs_char = EntryField(s3.inner, "Персонаж:", "cs_char",
                                    CFG, placeholder="все",
                                    tooltip="Имя одного персонажа для проверки. "
                                            "Пусто = проверить всех из реестра.")
        self.c_fix = CheckField(s3.inner, "Исправить старые имена (--fix)", "cs_fix",
                                CFG, default=False,
                                tooltip="Без галочки — только отчёт. С галочкой — "
                                        "заменяет старые имена на текущие (с бэкапом).")
        self.c_fix.pack(anchor="w")
        # 22.09: точечный фикс одного слова (--fix-word) — опечатки без реестра
        self.f_csw_bad = EntryField(s3.inner, "Слово (неверно):", "cs_word_bad", CFG,
                                    placeholder="Кайзо",
                                    tooltip="Найденное слово для замены: опечатка или "
                                            "старое имя. Заменяется ТОЛЬКО оно.")
        self.f_csw_good = EntryField(s3.inner, "Заменить на:", "cs_word_good", CFG,
                                     placeholder="Кайдзо",
                                     tooltip="Правильное написание.")
        self.c_fw_dry = CheckField(s3.inner, "Только отчёт (dry-run)", "cs_fw_dry",
                                   CFG, default=True,
                                   tooltip="С галочкой — показать что заменится. "
                                           "Без — реально заменить (с бэкапом).")
        self.c_fw_dry.pack(anchor="w")
        BigButton(s3.inner, "Проверить", self._run_char_search)
        self.b_fix_word = BigButton(s3.inner, "Заменить слово",
                                    self._run_char_fix_word,
                                    tooltip="Точечная замена одного слова по всем "
                                            ".md/.txt/.docx хранилища.")

        # --- 4. refile ---
        s4 = Section(parent, "4. Regex-замена по папке (refile)")
        self.f_rf = PathField(s4.inner, "Папка или файл:", "rf_dir", CFG, file_mode="both",
                              tooltip="Папка (обход рекурсивный) или один файл.")
        self.f_pat = EntryField(s4.inner, "Паттерн (regex):", "rf_pattern", CFG,
                                tooltip="Регулярное выражение. Пример: \\bИван\\b — "
                                        "слово Иван целиком.")
        self.f_repl = EntryField(s4.inner, "Замена:", "rf_repl", CFG,
                                 tooltip="Чем заменить. Пусто = удалить.")
        self.f_exts = EntryField(s4.inner, "Расширения:", "rf_exts", CFG,
                                 placeholder="md txt",
                                 tooltip="Какие файлы обрабатывать. Через пробел: md txt py js")
        self.c_rf = CheckField(s4.inner, "Применить изменения", "rf_apply", CFG,
                               default=False,
                               tooltip="Без галочки — dry-run. С галочкой — реально "
                                       "меняет файлы.")
        self.c_rf.pack(anchor="w")
        BigButton(s4.inner, "Запустить", self._run_refile)

    def _log(self, msg):
        from gui_ctk import _app
        _app.log_line(msg)

    def _run_md_replace(self):
        from gui_ctk import run_cmd
        vault = self.f_vault.get()
        old = self.f_old.get()
        if not vault or not old:
            self._log("Укажите хранилище и текст «Найти».\n")
            return
        run_cmd(cmd_md_replace(vault, old, self.f_new.get(),
                               is_regex=self.c_regex.get(),
                               dry_run=not self.c_apply.get(),
                               no_backup=self.c_nobak.get()))

    def _run_find_bad(self):
        from gui_ctk import run_cmd
        v = self.f_vault2.get()
        if not v:
            self._log("Укажите хранилище.\n")
            return
        run_cmd(cmd_md_find_bad(v))

    def _run_fix_encoding(self):
        from gui_ctk import run_cmd
        v = self.f_vault2.get()
        if not v:
            self._log("Укажите хранилище.\n")
            return
        run_cmd(cmd_md_fix_encoding(v, dry_run=not self.c_spec.get()))

    def _run_strip_bad(self):
        from gui_ctk import run_cmd
        v = self.f_vault2.get()
        if not v:
            self._log("Укажите хранилище.\n")
            return
        run_cmd(cmd_md_strip_bad(v, dry_run=not self.c_spec.get()))

    def _run_char_search(self):
        from gui_ctk import run_cmd
        v = self.f_cs_vault.get()
        if not v:
            self._log("Укажите хранилище.\n")
            return
        fix = self.c_fix.get()
        char = self.f_cs_char.get()
        cmd = cmd_char_search(v, char=char or None, fix=fix, dry_run=not fix)
        if not fix:
            cmd = [c for c in cmd if c != "--dry-run"]
        run_cmd(cmd)

    def _run_char_fix_word(self):
        # 22.09: точечная замена слова через --fix-word
        from gui_ctk import run_cmd
        from wrappers import cmd_char_fix_word
        v = self.f_cs_vault.get()
        bad = self.f_csw_bad.get()
        good = self.f_csw_good.get()
        if not v:
            self._log("Укажите хранилище.\n")
            return
        if not bad or not good:
            self._log("Укажите «Слово (неверно)» и «Заменить на».\n")
            return
        run_cmd(cmd_char_fix_word(v, bad, good, dry_run=self.c_fw_dry.get()))

    def _run_refile(self):
        from gui_ctk import run_cmd
        d = self.f_rf.get()
        pat = self.f_pat.get()
        if not d or not pat:
            self._log("Укажите папку и паттерн.\n")
            return
        exts = [e.strip() for e in self.f_exts.get().split() if e.strip()]
        run_cmd(cmd_refile(d, pat, replacement=self.f_repl.get(),
                           exts=exts or None, dry_run=not self.c_rf.get()))