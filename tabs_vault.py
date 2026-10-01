"""Вкладка «Хранилище»: orphan-finder, broken-links, merge-finder.
18.09: переделана на CustomTkinter (widgets_ctk)."""
import customtkinter as ctk

from gui_config import CFG
from widgets_ctk import PathField, CheckField, HelpBox, Section, BigButton, EntryField


class VaultTab(ctk.CTkFrame):
    LABEL = "Хранилище"

    def _build(self, parent):
        HelpBox(parent, text=(
            "Как это работает:\n"
            "Укажите папку хранилища (vault) — инструмент обойдёт все .md файлы внутри.\n"
            "• Orphans — заметки, на которые никто не ссылается и которые сами ни на кого не ссылаются "
            "(одиночки, возможно забыты).\n"
            "• Битые ссылки — ссылки [[вот так]], ведущие на несуществующую заметку.\n"
            "• Дубликаты — заметки с очень похожим содержимым или почти одинаковым именем — "
            "кандидаты на слияние.\n"
            "Все три инструмента ТОЛЬКО читают файлы — ничего не изменяют."))

        s = Section(parent, "Хранилище (vault)")
        self.f_vault = PathField(s.inner, "Папка vault:", "vault_input", CFG,
                                 file_mode="both",
                                 tooltip="Обычно это папка хранилища Obsidian "
                                         "(например Daro Coding) — обход рекурсивный. "
                                         "Но можно выбрать и один .md файл — "
                                         "инструмент проверит только его.")

        btns = ctk.CTkFrame(s.inner, fg_color="transparent")
        btns.pack(fill="x", pady=6)
        BigButton(btns, "Orphans (одиночки)", self._run_orphans,
                  tooltip="Заметки без входящих и исходящих ссылок.").pack(
                      side="left", padx=(0, 8))
        BigButton(btns, "Битые ссылки", self._run_broken,
                  tooltip="Ссылки [[такие]], ведущие на несуществующие заметки.").pack(
                      side="left", padx=8)
        BigButton(btns, "Дубликаты (merge)", self._run_merge,
                  tooltip="Похожие заметки — кандидаты на слияние.").pack(
                      side="left", padx=8)

        self.c_report = CheckField(s.inner, "Сохранять отчёт в reports/", "vault_save_report", CFG,
                                   tooltip="Кроме окна, отчёт будет записан в папку reports/ внутри textools.")
        self.c_report.pack(anchor="w", pady=(0, 4))

        # --- 22.09: phrase_check — штампы ИИ-текста и канцелярит ---
        s2 = Section(parent, "Штампы ИИ-текста и канцелярит (phrase_check)")
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
        btns_pc = ctk.CTkFrame(s2.inner, fg_color="transparent")
        btns_pc.pack(fill="x", pady=6)
        BigButton(btns_pc, "Найти штампы", self._run_phrase_check,
                  tooltip="Ищет шаблонные нейросетевые обороты и канцелярит по всем "
                          ".md/.txt/.docx. Только отчёт, ничего не изменяет."
                  ).pack(side="left", padx=(0, 8))
        self.c_pc_dry = CheckField(btns_pc, "Только отчёт (не менять)", "pc_dry", CFG,
                                   default=True,
                                   tooltip="ВКЛ — показывается план замен без правки файлов. "
                                           "ВЫКЛ — реальные замены (с бэкапом).")
        self.c_pc_dry.pack(side="left", padx=(0, 12))
        BigButton(btns_pc, "Почистить штампы", self._run_phrase_clean,
                  tooltip="Удаляет/заменяет штампы по словарю очистки "
                          "(phrases_clean.yaml можно дополнить своими правилами). "
                          "Например: «в современном мире» -> «сегодня», "
                          "«стоит отметить, что» -> удалить. С бэкапом.")
        # 01.10: витрина — каждое вхождение с контекстом и галочками
        self.c_pc_review = CheckField(btns_pc, "Выборочно (витрина)",
                                      "pc_review", CFG, default=False,
                                      tooltip="Показать каждое вхождение "
                                              "с контекстом и выбрать, что "
                                              "чистить. Работает с кнопкой "
                                              "«Почистить штампы».")
        self.c_pc_review.pack(side="left")

        # --- Статистика текста (01.10) ---
        s3 = Section(parent, "Статистика текста (объём, диалоги, паразиты)")
        self.f_stats = PathField(s3.inner, "Папка или файл:", "stats_input", CFG,
                                 file_mode="both",
                                 tooltip="Папка с текстами (.md/.txt/.docx) или "
                                         "один файл. Только чтение.")
        BigButton(s3.inner, "Построить статистику", self._run_stats,
                  tooltip="Объём, средняя длина предложения, доля диалогов, "
                          "частотные слова-паразиты на 1000 слов.")

    def _log(self, msg):
        # 01.10: раньше не было — кнопки штампов падали с AttributeError
        from gui_ctk import _app
        _app.log_line(msg)

    def _run(self, modname):
        from gui_ctk import run_internal, _app
        path = self.f_vault.get()
        if not path:
            _app.log_line("Укажите папку vault.\n")
            return
        args = ["--input", path]
        # 18.09: vault_save_report теперь реально пишет отчёт в reports/
        if self.c_report.get():
            from gui_config import CONFIG_FILE
            reports = CONFIG_FILE.parent / "reports"
            reports.mkdir(exist_ok=True)
            args += ["--out", str(reports / f"{modname}.md")]
        run_internal(modname, args)

    def _run_orphans(self):
        self._run("orphan_finder")

    def _run_broken(self):
        self._run("broken_links")

    def _run_merge(self):
        self._run("merge_finder")

    def _run_phrase_check(self):
        # 22.09: phrase_check — штампы ИИ-текста и канцелярит
        from gui_ctk import run_cmd
        from gui_config import CONFIG_FILE
        p = self.f_pc.get()
        if not p:
            self._log("Укажите папку или файл для поиска штампов.\n")
            return
        phrase = self.f_pc_phrase.get()
        custom = self.f_pc_custom.get()
        # 22.09: «запомнить» — добавляем фразу в постоянный словарь
        # 01.10: subprocess в фоновом потоке — не блокируем интерфейс
        if phrase and self.c_pc_add.get():
            import subprocess
            import threading
            script = str(CONFIG_FILE.parent / "tools" / "phrase_check.py")

            def _add_phrase():
                r = subprocess.run(
                    ["python", script, "--add", phrase],
                    capture_output=True, text=True, encoding="utf-8", timeout=30)
                if r.returncode == 0 and r.stdout:
                    self._log(r.stdout)

            threading.Thread(target=_add_phrase, daemon=True).start()
        cmd = ["python", str(CONFIG_FILE.parent / "tools" / "phrase_check.py"),
               "--input", p]
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
        from gui_config import CONFIG_FILE
        p = self.f_pc.get()
        if not p:
            _app.log_line("Укажите папку или файл для чистки штампов.\n")
            return
        if self.c_pc_review.get():
            self._run_review(p)
            return
        dry = self.c_pc_dry.get()
        script = CONFIG_FILE.parent / "tools" / "phrase_check.py"
        cmd = ["python", str(script), "--input", p, "--clean"]
        if dry:
            cmd += ["--dry-run"]
        else:
            cmd += ["--yes"]
        _app.log_line(
            f"{'План чистки (dry-run)' if dry else 'ЧИСТКА (реальная замена)'}: "
            f"{p} — прогресс внизу над логом...\n")
        run_cmd(cmd)

    def _run_stats(self):
        from gui_ctk import run_internal
        if not self.f_stats.get():
            self._log("Укажите папку или файл.\n")
            return
        run_internal("text_stats", ["--input", self.f_stats.get()])

    def _run_review(self, path):
        # 01.10: витрина — subprocess собирает вхождения, диалог даёт выбрать.
        # Поток кладёт результат в очередь, главный поток опрашивает через
        # after() (звать after из чужого потока нельзя: main thread is not
        # in main loop)
        import queue as _queue
        import subprocess
        import threading
        from gui_config import CONFIG_FILE
        script = str(CONFIG_FILE.parent / "tools" / "phrase_check.py")
        q = _queue.Queue()

        def _worker():
            r = subprocess.run(
                ["python", script, "--input", path, "--review"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=600)
            hits = []
            for line in (r.stdout or "").splitlines():
                if line.startswith("REVIEW\t"):
                    parts = line.split("\t", 5)
                    if len(parts) == 6:
                        hits.append((parts[1], parts[2], parts[3],
                                     parts[4], parts[5]))
            q.put(hits)

        def _check():
            try:
                hits = q.get_nowait()
            except _queue.Empty:
                from gui_ctk import _app as app
                app.after(150, _check)
                return
            self._open_review(hits)

        threading.Thread(target=_worker, daemon=True).start()
        from gui_ctk import _app as app
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
            for msg in phrase_check.clean_selection(pairs):
                _app.log_line(msg + "\n",
                              "ok" if msg.startswith("[ОЧИЩЕН]") else None)

        import review_dialog
        review_dialog.show(_app, hits, _apply)