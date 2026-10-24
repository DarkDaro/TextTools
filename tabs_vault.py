"""Вкладка «Хранилище»: orphan-finder, broken-links, merge-finder, integrity,
obsidian-check и поиск иероглифов (find_cjk).
18.09: переделана на CustomTkinter (widgets_ctk)."""
import sys
from pathlib import Path

import customtkinter as ctk

from gui_config import CFG
from widgets_ctk import (PathField, CheckField, HelpBox, Section,
                         EntryField, ActionButton, button_row)

HERE = Path(__file__).resolve().parent


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
        ActionButton(btns, "Orphans (одиночки)", self._run_orphans,
                     kind="safe", width=170,
                     tooltip="Заметки без входящих и исходящих ссылок."
                     ).pack(side="left", padx=(0, 8))
        ActionButton(btns, "Битые ссылки", self._run_broken,
                     kind="safe", width=165,
                     tooltip="Ссылки [[такие]], ведущие на несуществующие заметки."
                     ).pack(side="left", padx=(0, 8))
        ActionButton(btns, "Дубликаты (merge)", self._run_merge,
                     kind="safe", width=175,
                     tooltip="Похожие заметки — кандидаты на слияние."
                     ).pack(side="left", padx=(0, 8))
        ActionButton(btns, "Целостность", self._run_integrity,
                     kind="safe", width=150,
                     tooltip="Пустые файлы, битый UTF-8, незакрытый frontmatter, "
                             "отсутствие заголовка ##. Только чтение."
                     ).pack(side="left")

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
        self.c_stats_csv = CheckField(s3.inner, "Дописывать в CSV-дневник",
                                      "stats_csv", CFG, default=False,
                                      tooltip="Каждый запуск добавляет строку "
                                              "«дата; файл; слова; …» в "
                                              "reports/stats_log.csv — удобно "
                                              "следить за прогрессом в Excel.")
        self.c_stats_csv.pack(anchor="w")
        row_stats = button_row(s3.inner)
        ActionButton(row_stats, "Построить статистику", self._run_stats,
                     kind="safe", width=235,
                     tooltip="Объём, средняя длина предложения, доля диалогов, "
                             "частотные слова-паразиты на 1000 слов."
                     ).pack(side="left")

        # --- Стилистика (03.10) ---
        s4 = Section(parent, "Стилистика: повторы рядом и длинные предложения")
        self.f_style = PathField(s4.inner, "Папка или файл:", "style_input", CFG,
                                 file_mode="both",
                                 tooltip="Папка с текстами (.md/.txt/.docx) или "
                                         "один файл. Только чтение, файлы "
                                         "не изменяются.")
        self.f_style_reg = EntryField(s4.inner, "Реестр персонажей (yaml):",
                                      "style_registry", CFG,
                                      placeholder="необязательно",
                                      tooltip="Формы имён из реестра "
                                              "не будут считаться повторами.")
        r4 = ctk.CTkFrame(s4.inner, fg_color="transparent")
        r4.pack(fill="x", pady=2)
        self.e_style_window = EntryField(r4, "Окно повтора (слов):",
                                         "style_window", CFG, placeholder="5",
                                         width_label=150,
                                         tooltip="Слово считается повтором, "
                                                 "если встретилось второй раз "
                                                 "в пределах этого числа слов.")
        self.e_style_window.pack(side="left", padx=(0, 12))
        self.e_style_long = EntryField(r4, "Длинное предложение (слов):",
                                       "style_long", CFG, placeholder="25",
                                       width_label=190,
                                       tooltip="Предложения длиннее этого числа "
                                               "слов попадают в отчёт.")
        self.e_style_long.pack(side="left", padx=0)
        row_style = button_row(s4.inner)
        ActionButton(row_style, "Построить стилистический отчёт", self._run_style,
                     kind="safe", width=260,
                     tooltip="Повторы слов в пределах окна (тавтологии, кроме "
                             "служебных и форм имён) и слишком длинные "
                             "предложения. Файлы не изменяются."
                     ).pack(side="left")

    def _log(self, msg, tag=None):
        # 01.10: раньше не было — кнопки штампов падали с AttributeError
        from gui_ctk import _app
        _app.log_line(msg, tag)

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
        args = ["--input", p, "--exit-zero"]
        if self.c_obs_fix.get():
            args.append("--fix")
            # 24.10: настройка «не создавать .bak» (папки под git)
            if CFG.get("obs_no_bak", False) is True:
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
        cmd = [sys.executable,
               str(HERE / "find_cjk.py"), p]
        ext = str(CFG.get("cjk_ext", "") or "").strip()
        if ext:
            cmd += ["--ext", ext]
        if self.c_cjk_json.get():
            reports = _app._reports_dir()
            cmd += ["--json", str(reports / "cjk_report.json")]
        run_cmd(cmd)

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
        # 24.10: делаем это до поиска и в главном потоке: короткий запуск
        # скрипта, зато лог не пишется из чужого потока (Tk так нельзя).
        if phrase and self.c_pc_add.get():
            import subprocess
            script = str(HERE / "tools" / "phrase_check.py")
            try:
                r = subprocess.run(
                    [sys.executable, script, "--add", phrase],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=30)
                if r.returncode == 0 and r.stdout:
                    self._log(r.stdout)
                else:
                    self._log("Не удалось запомнить фразу в словарь.\n",
                              "warn")
            except Exception as e:
                self._log(f"Не удалось запомнить фразу: {e}\n", "warn")
        cmd = [sys.executable,
               str(HERE / "tools" / "phrase_check.py"),
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
        p = self.f_pc.get()
        if not p:
            _app.log_line("Укажите папку или файл для чистки штампов.\n")
            return
        if self.c_pc_review.get():
            self._run_review(p)
            return
        dry = self.c_pc_dry.get()
        script = HERE / "tools" / "phrase_check.py"
        cmd = [sys.executable, str(script), "--input", p, "--clean"]
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
        args = ["--input", self.f_stats.get()]
        # 03.10: CSV-дневник объёма (reports/stats_log.csv)
        if self.c_stats_csv.get():
            args.append("--csv")
        run_internal("text_stats", args)

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

    def _run_review(self, path):
        # 01.10: витрина — subprocess собирает вхождения, диалог даёт выбрать.
        # Поток кладёт результат в очередь, главный поток опрашивает через
        # after() (звать after из чужого потока нельзя: main thread is not
        # in main loop). 24.10: задача идёт через общий «занято», «Стоп»
        # умеет завершить процесс.
        import queue as _queue
        import subprocess
        import threading
        from gui_ctk import _app as app

        if not app.begin_background("Витрина штампов"):
            return
        script = str(HERE / "tools" / "phrase_check.py")
        q = _queue.Queue()

        def _worker():
            # 20.10: любой сбой (таймаут, нет интерпретатора) кладёт в
            # очередь маркер — раньше полл после ошибки крутился вечно
            import sys
            proc = None
            try:
                proc = subprocess.Popen(
                    [sys.executable, script, "--input", path, "--review"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW)
                app._bg_proc = proc
                out, _ = proc.communicate(timeout=600)
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                except Exception:
                    pass
                q.put(("err", "Витрина не успела за 10 минут и была "
                              "остановлена.\n"))
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
