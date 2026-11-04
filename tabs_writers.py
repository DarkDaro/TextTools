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
            "Безопасность: по умолчанию всё только читает и пишет отчёт. "
            "Реальная запись — по галочке, с бэкапом (.bak рядом с файлом)."))

        # --- 1. АНТИРЕШИМОСТЬ (05.11: переехала из «Чистки») ---
        s1 = Section(parent,
                     "1. АНТИРЕШИМОСТЬ — запрещённая лексика и пафос "
                     "(txt / md / docx)")
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
        ctk.CTkLabel(s1.inner, justify="left", anchor="w", font=FONT_SMALL, text=(
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
        s2 = Section(parent, "2. Штампы ИИ-текста и канцелярит (phrase_check)")
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
        self.c_pc_review = CheckField(btns_pc, "Выборочно (витрина)",
                                      "pc_review", CFG, default=False,
                                      tooltip="Показать каждое вхождение "
                                              "с контекстом и выбрать, что "
                                              "чистить. Работает с кнопкой "
                                              "«Почистить штампы».")
        self.c_pc_review.pack(side="left")

        # --- 3. стилистика (переехала из «Хранилища») ---
        s3 = Section(parent, "3. Стилистика: повторы рядом и длинные предложения")
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
        s4 = Section(parent, "4. Статистика текста (объём, диалоги, паразиты)")
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
        s5 = Section(parent, "5. Ё/Е-аудит (спорные места с ё)")
        self.f_yo_input = PathField(s5.inner, "Тексты (папка/файл):", "yo_input",
                                    CFG, file_mode="both",
                                    tooltip="Папка или файл .md/.txt. Правки "
                                            "применяются только к .md/.txt.")
        self.f_yo_reg = PathField(s5.inner, "Реестр (yaml):", "yo_registry", CFG,
                                  file_mode="file",
                                  tooltip="Реестр персонажей: имена с ё (Семён) "
                                          "сверяются с написанием в тексте (Семен).")
        row5 = button_row(s5.inner)
        ActionButton(row5, "Ё/Е-аудит (витрина)", self._run_yo,
                     kind="safe", width=235,
                     tooltip="Собирает спорные места: имена из реестра, словарные "
                             "пары и омографы (все/всё). Замена — только по "
                             "выбранным вхождением в диалоге."
                     ).pack(side="left")

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
                # docx в этой итерации не правится (решение пользователя)
                hits = [h for h in hits
                        if not h[2].lower().endswith(".docx")]
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
