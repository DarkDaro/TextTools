"""Вкладка «Помодоро»: трекер времени писателя по технике Pomodoro.

18.11: бонус-фича по запросу владельца — таймер 25/5/15 с помидорами
и счётчиками дня. Логика фаз живёт в core/pomodoro.py (чистая машина
состояний, покрыта тестами test/test_pomodoro.py); вкладка только
рисует состояние движка и кормит его тиками по настенным часам
(after-цикл раз в полсекунды, движок получает целые секунды —
подвисание окна не собьёт отсчёт).

Длительности, серия и автостарт задаются на вкладке «Настройки»
(раздел «Помодоро», те же ключи конфига): правки едут сюда мгновенно
(трейс полей «Настроек») и, как страховка, перечитываются на каждом
такте цикла. Пустые и нечисловые значения дают классику — так же их
решает и перезапуск программы.

Почему нет CLI-версии: интерактивный таймер — живой интерфейс
(обратный отсчёт на экране, пауза, подсказка в конце фазы); строка
с обоснованием есть в docs/CLI_GUI_MAP.md. Движок при этом общий —
если CLI-режим понадобится, он переиспользует тот же класс.

Статистика дня: ключ pomo.stats в gui_config.json
({"day": "YYYY-MM-DD", "work_done": N, "work_seconds": M}) —
на новую дату счётчики откатываются в ноль (ensure_day)."""
import time
import customtkinter as ctk

from gui_config import CFG
from widgets_ctk import (HelpBox, Section, ActionButton, button_row,
                         FONT, FONT_SECTION, MONO_FAMILY)
from core.pomodoro import (PHASE_TITLES, WORK, DEFAULTS, PomodoroEngine,
                           clamp_min, clamp_rounds, ensure_day, fmt_mmss,
                           session_report_lines)

# цвета фаз: пара (светлая, тёмная) — CTk сам выбирает по теме.
# Работа — фирменный фиолетовый акцент, перерывы — спокойный зелёный.
COLOR_WORK = ("#5b21b6", "#c4b5fd")
COLOR_BREAK = ("#15803d", "#4ade80")


def _today():
    return time.strftime("%Y-%m-%d")


def _cfg_bool(key, default):
    """Булев ключ конфига: в JSON может оказаться строка «false»."""
    v = CFG.get(key, default)
    if isinstance(v, str):
        v = v.strip().lower() not in ("", "false", "0", "no")
    return bool(v)


def _fmt_total(seconds):
    """Чистое время работы по-человечески: до часа «N мин», дальше
    «H ч M мин»."""
    m = max(0, int(seconds)) // 60
    if m < 60:
        return f"{m} мин"
    return f"{m // 60} ч {m % 60} мин"


class PomodoroTab(ctk.CTkFrame):
    LABEL = "Помодоро"

    def _build(self, parent):
        HelpBox(parent, key="pomodoro", text=(
            "Как это работает:\n"
            "• Помодоро — техника тайм-менеджмента писателя: 25 минут "
            "работы без отвлечений, затем 5 минут перерыва; после 4 "
            "помидоров подряд — длинный перерыв 15 минут.\n"
            "• Нажмите «Старт» — таймер сам посчитает фазы и подскажет, "
            "когда отдохнуть: звук и всплывающая подсказка в конце фазы. "
            "«Пропустить фазу» ведёт к следующей сразу, пропущенная "
            "работа в счёт не идёт; с паузы пропуск следующую фазу "
            "сам не запускает.\n"
            "• Длительности, серия и автостарт задаются на вкладке "
            "«Настройки» (раздел «Помодоро», есть пресет 50/10) и "
            "применяются со следующей фазы; пока таймер стоит в начале "
            "фазы — сразу. По классике перерыв начинается сам, а работу "
            "начинает автор.\n"
            "• Поле «Задача» называет работу цикла: название попадает "
            "в журнал сессии и в итоговый отчёт. Кнопка «Отвлечение» "
            "записывает причину, пауза дольше 5 минут в работе помечает "
            "цикл прерванным.\n"
            "• Счётчики дня (раздел 2) ведутся по датам: в полночь "
            "начинаются с нуля. Статистика хранится офлайн — в "
            "gui_config.json рядом с программой.\n"
            "• Всё работает без сети: таймер живёт в окне программы."))

        # --- движок и дневные счётчики ---
        self.engine = PomodoroEngine(
            work_min=CFG.get("pomo.work_min", 25),
            short_min=CFG.get("pomo.short_min", 5),
            long_min=CFG.get("pomo.long_min", 15),
            rounds=CFG.get("pomo.rounds", 4),
            auto_break=_cfg_bool("pomo.auto_break", True),
            auto_work=_cfg_bool("pomo.auto_work", False))
        loaded = CFG.get("pomo.stats", {})
        self._stats = ensure_day(loaded, _today())
        if self._stats != loaded:
            self._save_stats()
        self._seen_done = 0          # засчитанное время на момент прошлой записи
        self._last_ts = time.monotonic()

        # --- 1. таймер ---
        s1 = Section(parent, "1. Таймер",
                     subtitle="классика: 25 работы · 5 перерыв · "
                              "15 после 4 помидоров · пресет 50/10 — "
                              "в «Настройках»")
        row_task = ctk.CTkFrame(s1.inner, fg_color="transparent")
        row_task.pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(row_task, text="Задача:", font=FONT).pack(side="left")
        self.e_task = ctk.CTkEntry(row_task, width=280, font=FONT,
                                   placeholder_text="над чем работаете?")
        self.e_task.pack(side="left", padx=(8, 0), fill="x", expand=True)
        self.lbl_time = ctk.CTkLabel(
            s1.inner, text=fmt_mmss(self.engine.remaining),
            font=(MONO_FAMILY, 44, "bold"), text_color=COLOR_WORK)
        self.lbl_time.pack(pady=(0, 2))
        self.lbl_phase = ctk.CTkLabel(s1.inner, text="", font=FONT_SECTION)
        self.lbl_phase.pack()
        self.lbl_series = ctk.CTkLabel(s1.inner, text="", font=FONT,
                                       text_color=("gray40", "gray60"))
        self.lbl_series.pack(pady=(0, 2))
        row1 = button_row(s1.inner)
        self.b_start = ActionButton(
            row1, "Старт", self._on_start_pause, kind="primary", width=130,
            tooltip="Начать отсчёт (или поставить на паузу). В конце фазы "
                    "таймер подскажет звуком и всплывающей подсказкой.")
        self.b_start.pack(side="left", pady=(8, 0))
        self.b_reset = ActionButton(
            row1, "Сброс", self._on_reset, kind="neutral", width=110,
            tooltip="Вернуть текущую фазу к полной длительности и "
                    "остановить отсчёт.")
        self.b_reset.pack(side="left", padx=8, pady=(8, 0))
        self.b_skip = ActionButton(
            row1, "Пропустить фазу", self._on_skip, kind="neutral",
            width=180,
            tooltip="Сразу перейти к следующей фазе. Пропущенная работа "
                    "в счёт помидоров не идёт. С паузы следующая фаза "
                    "ждёт «Старт».")
        self.b_skip.pack(side="left", pady=(8, 0))
        row1b = button_row(s1.inner)
        self.b_interrupt = ActionButton(
            row1b, "Отвлечение", self._on_interrupt, kind="neutral",
            width=150,
            tooltip="Записать, что отвлекло от работы: причина попадёт "
                    "в журнал сессии и в итоговый отчёт.")
        self.b_interrupt.pack(side="left", pady=(2, 0))
        self.b_report = ActionButton(
            row1b, "Итог сессии", self._on_report, kind="neutral",
            width=160,
            tooltip="Завершить сессию и показать итог: помидоры, "
                    "задача, отвлечения, журнал. Таймер останавливается.")
        self.b_report.pack(side="left", padx=8, pady=(2, 0))

        # --- 2. сегодня ---
        s_today = Section(parent, "2. Сегодня",
                          subtitle="в полночь счётчики начинаются с нуля")
        self.lbl_done = ctk.CTkLabel(s_today.inner, text="", font=FONT,
                                     anchor="w")
        self.lbl_done.pack(anchor="w")
        self.lbl_total = ctk.CTkLabel(s_today.inner, text="", font=FONT,
                                      anchor="w")
        self.lbl_total.pack(anchor="w")
        row3 = button_row(s_today.inner)
        self.b_zero = ActionButton(
            row3, "Обнулить счётчик", self._on_zero, kind="neutral",
            width=180,
            tooltip="Сбросить дневные помидоры и чистое время работы. "
                    "Сам таймер не трогается.")
        self.b_zero.pack(side="left")

        self._refresh()
        # тики: полсекунды — движку уходят целые секунды по настенным
        # часам, поэтому кратковременное подвисание окна отсчёт не собьёт
        self.after(500, self._loop)

    # --- журнал и уведомления ---

    def _log(self, msg):
        try:
            from gui_ctk import _app
            _app.log_line(msg + "\n")
        except Exception:
            pass

    def _notify(self, text, level="info", beep=True):
        """Всплывающая подсказка; звук — по галочке «pomo.sound», общий
        переключатель звука проверяется внутри тоста."""
        try:
            from gui_ctk import _app
            _app.toast(text, level, beep=beep and
                       _cfg_bool("pomo.sound", True))
        except Exception:
            pass

    # --- статистика дня ---

    def _save_stats(self):
        CFG.set("pomo.stats", dict(self._stats))

    # --- синхронизация с настройками ---

    def _apply_cfg(self):
        """Длительности и автостарт — из конфига (вкладка «Настройки»,
        раздел «Помодоро»). Пустые и нечисловые значения дают
        классические 25/5/15/4 — как обещают подсказки полей и как
        при перезапуске программы. Правка применяется к следующей
        фазе; пока таймер стоит в начале фазы — сразу (движок сам
        решает, когда перезаряжать отсчёт). Вызывается из трейсов
        «Настроек» и на каждом такте цикла — дёшево и идемпотентно."""
        self.engine.set_durations(
            work_min=clamp_min(CFG.get("pomo.work_min",
                                       DEFAULTS["work_min"]),
                               DEFAULTS["work_min"]),
            short_min=clamp_min(CFG.get("pomo.short_min",
                                        DEFAULTS["short_min"]),
                                DEFAULTS["short_min"]),
            long_min=clamp_min(CFG.get("pomo.long_min",
                                       DEFAULTS["long_min"]),
                               DEFAULTS["long_min"]),
            rounds=clamp_rounds(CFG.get("pomo.rounds",
                                        DEFAULTS["rounds"]),
                                DEFAULTS["rounds"]))
        self.engine.auto_break = _cfg_bool("pomo.auto_break", True)
        self.engine.auto_work = _cfg_bool("pomo.auto_work", False)

    def _pump_day(self):
        """Новый день — счётчики в ноль (проверка на каждом тике)."""
        today = _today()
        if self._stats.get("day") != today:
            self._stats = {"day": today, "work_done": 0, "work_seconds": 0}
            self._save_stats()
            self._log("Помодоро: новый день — счётчики обнулены.")

    # --- цикл таймера ---

    def _loop(self):
        try:
            self._pump_day()
            self._apply_cfg()
            if self.engine.running:
                now = time.monotonic()
                whole = int(now - self._last_ts)
                if whole >= 1:
                    self._last_ts += whole
                    for ev in self.engine.tick(whole):
                        self._on_event(ev)
            else:
                self._last_ts = time.monotonic()
            self._refresh()
        except Exception:
            pass  # вкладка не должна ронять приложение
        try:
            self.after(500, self._loop)
        except Exception:
            pass  # окно закрывается

    def _on_event(self, ev):
        kind, value = ev
        if kind == "phase_end":
            self._log(f"Помодоро: «{PHASE_TITLES[value]}» завершена.")
            self._notify(f"{PHASE_TITLES[value]} — время вышло", "ok")
        elif kind == "work_done":
            done = self.engine.done_work_seconds - self._seen_done
            self._seen_done = self.engine.done_work_seconds
            self._stats["work_done"] = int(self._stats.get("work_done", 0)) + 1
            self._stats["work_seconds"] = (int(self._stats.get(
                "work_seconds", 0)) + done)
            self._save_stats()
            self._log(f"Помодоро: помидор {value} в серии засчитан — "
                      f"сегодня {self._stats['work_done']}, "
                      f"чистое время {_fmt_total(self._stats['work_seconds'])}.")
        elif kind == "phase_start":
            title = PHASE_TITLES[value]
            secs = fmt_mmss(self.engine.state()["durations"][value])
            self._log(f"Помодоро: {title.lower()} {secs}.")
            self._notify(f"{title} — {secs}", "info", beep=False)

    # --- кнопки ---

    def _on_start_pause(self):
        if self.engine.running:
            self.engine.pause()
            self._log(f"Помодоро: пауза — осталось "
                      f"{fmt_mmss(self.engine.remaining)}.")
        else:
            # свежие настройки «Настроек» сразу: цикл подхватил бы их
            # за полсекунды, но старт в тот же миг — честнее применить
            self._apply_cfg()
            self.engine.set_task(self.e_task.get())
            self.engine.start()
            self._last_ts = time.monotonic()
            self._log(f"Помодоро: {PHASE_TITLES[self.engine.phase].lower()} "
                      f"{fmt_mmss(self.engine.remaining)} — вперёд.")
        self._refresh()

    def _on_reset(self):
        self.engine.reset()
        self._log(f"Помодоро: сброс — {PHASE_TITLES[self.engine.phase].lower()} "
                  f"{fmt_mmss(self.engine.remaining)}, отсчёт стоит.")
        self._refresh()

    def _on_skip(self):
        prev = self.engine.phase
        self.engine.skip()
        self._log(f"Помодоро: «{PHASE_TITLES[prev]}» пропущена — дальше "
                  f"{PHASE_TITLES[self.engine.phase].lower()} "
                  f"{fmt_mmss(self.engine.remaining)}.")
        self._refresh()

    def _on_zero(self):
        self._stats = {"day": _today(), "work_done": 0, "work_seconds": 0}
        self._save_stats()
        self._log("Помодоро: дневные счётчики обнулены, таймер не тронут.")
        self._refresh()

    def _on_interrupt(self):
        """«Отвлечение» — диалог причины (из ревью порция 3); причина
        в движок: список + журнал. Пустой ввод — «без причины».
        Окно само закрывается через секунду-полторы, отсчёт не трогает."""
        try:
            dlg = ctk.CTkInputDialog(
                text="Что отвлекло? (Enter — записать, Esc — отмена)",
                title="Помодоро — отвлечение")
            reason = (dlg.get_input() or "").strip()
        except Exception:
            return
        if reason is None:
            return  # Esc/закрытие окна — ничего не записываем
        self.engine.add_interruption(reason)
        self._log(f"Помодоро: отвлечение записано — «{reason or 'без причины'}».")
        self._refresh()

    def _on_report(self):
        """«Итог сессии» — завершить сессию и показать отчёт (формат
        ревью порций 1–2). Отсчёт останавливается; дневные счётчики
        не трогаются (они уже учтены по ходу работы)."""
        rep = self.engine.finish_session()
        lines = session_report_lines(rep)
        self._log("Помодоро: сессия завершена — "
                  f"помидоров {rep['done_pomodoros']}, "
                  f"отвлечений {len(rep['interruptions'])}.")
        self._notify("Сессия завершена — итог на экране", "ok")
        self._show_report_window("Помодоро — итог сессии", lines)
        self._refresh()

    def _show_report_window(self, title, lines):
        try:
            dlg = ctk.CTkToplevel(self)
            dlg.title(title)
            dlg.geometry("640x480")
            dlg.transient(self.winfo_toplevel())
            box = ctk.CTkTextbox(dlg, font=(MONO_FAMILY, 12), wrap="word")
            box.pack(fill="both", expand=True, padx=10, pady=(10, 6))
            box.insert("1.0", "\n".join(lines))
            box.configure(state="disabled")
            ctk.CTkButton(dlg, text="Закрыть", width=120,
                          command=dlg.destroy).pack(pady=(0, 10))
            dlg.after(200, dlg.lift)
        except Exception:
            pass  # окно закрывается — отчёт остаётся в журнале приложения

    # --- отображение ---

    def _phase_text(self, st):
        title = PHASE_TITLES[st["phase"]]
        if st["running"]:
            return f"{title} — идёт"
        if st["remaining"] == st["durations"][st["phase"]]:
            return f"{title} — готова к старту"
        return f"{title} — пауза"

    def _refresh(self):
        st = self.engine.state()
        color = COLOR_WORK if st["phase"] == WORK else COLOR_BREAK
        try:
            self.lbl_time.configure(text=fmt_mmss(st["remaining"]),
                                    text_color=color)
            self.lbl_phase.configure(text=self._phase_text(st))
            self.lbl_series.configure(
                text=f"Серия: {st['round_in_series']} из {st['rounds']} "
                     f"помидоров")
            self.b_start.configure(
                text="Пауза" if st["running"] else "Старт")
            self.lbl_done.configure(
                text=f"Помидоров сегодня: "
                     f"{int(self._stats.get('work_done', 0))}")
            self.lbl_total.configure(
                text=f"Чистое время работы: "
                     f"{_fmt_total(self._stats.get('work_seconds', 0))}")
        except Exception:
            pass
