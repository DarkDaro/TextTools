"""Вкладка «Помодоро»: трекер времени писателя по технике Pomodoro.

23.11: бонус-фича по запросу владельца — таймер 25/5/15 с помидорами,
счётчиками дня и настройками длительностей. Логика фаз живёт в
core/pomodoro.py (чистая машина состояний, покрыта тестами
test/test_pomodoro.py); вкладка только рисует состояние движка и
кормит его тиками по настенным часам (after-цикл раз в полсекунды,
движок получает целые секунды — подвисание окна не собьёт отсчёт).

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
from widgets_ctk import (CheckField, EntryField, HelpBox, Section,
                         ActionButton, button_row, FONT, FONT_SECTION,
                         FONT_SMALL, MONO_FAMILY)
from core.pomodoro import (PHASE_TITLES, SHORT, LONG, WORK, PomodoroEngine,
                           ensure_day, fmt_mmss)

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
            "работа в счёт не идёт.\n"
            "• Длительности и автостарт (раздел 2) применяются со "
            "следующей фазы; пока таймер стоит, новая длительность видна "
            "сразу. По классике перерыв начинается сам, а работу "
            "начинает автор.\n"
            "• Счётчики дня (раздел 3) ведутся по датам: в полночь "
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
                              "15 после 4 помидоров")
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
                    "в счёт помидоров не идёт.")
        self.b_skip.pack(side="left", pady=(8, 0))

        # --- 2. длительности и автостарт ---
        s2 = Section(parent, "2. Длительности и автостарт",
                     subtitle="применяются со следующей фазы")
        self.e_work = EntryField(
            s2.inner, "Работа, мин:", "pomo.work_min", CFG,
            width_label=210, placeholder="25",
            tooltip="Длительность сфокусированной работы: от 1 до 240 "
                    "минут. Пусто — классические 25.")
        self.e_short = EntryField(
            s2.inner, "Короткий перерыв, мин:", "pomo.short_min", CFG,
            width_label=210, placeholder="5",
            tooltip="Пауза после каждого помидора. Пусто — 5 минут.")
        self.e_long = EntryField(
            s2.inner, "Длинный перерыв, мин:", "pomo.long_min", CFG,
            width_label=210, placeholder="15",
            tooltip="Отдых после всей серии помидоров. Пусто — 15 минут.")
        self.e_rounds = EntryField(
            s2.inner, "Помидоров до длинного перерыва:", "pomo.rounds",
            CFG, width_label=210, placeholder="4",
            tooltip="Сколько помидоров в серии. Пусто — 4.")
        self.c_auto_break = CheckField(
            s2.inner, "Автоматически начинать перерыв", "pomo.auto_break",
            CFG, default=True,
            tooltip="Фаза работы кончилась — перерыв стартует сам, "
                    "чтобы отдохнуть не забыть.")
        self.c_auto_work = CheckField(
            s2.inner, "Автоматически начинать работу", "pomo.auto_work",
            CFG, default=False,
            tooltip="Перерыв кончился — новая работа стартует сама. "
                    "По умолчанию выключено: когда садиться писать, "
                    "решает автор.")
        self.c_sound = CheckField(
            s2.inner, "Звук в конце фазы", "pomo.sound", CFG, default=True,
            tooltip="В конце фазы — системный звук и всплывающая "
                    "подсказка. Общий звук программы (галочка «Звуковые "
                    "сигналы» на «Настройках») тоже учитывается.")

        # 23.11: читаем var НАПРЯМУЮ, а не get(): трейсы Tk-переменных
        # срабатывают в порядке LIFO — наш обработчик идёт раньше
        # _sync_entry поля, и get() в этот момент через _on_edit видит
        # рассинхрон entry/var и откатывает var в пустоту (настройка
        # молча не применялась). var в момент трейса уже новый.
        def _apply_settings(*_):
            self.engine.set_durations(
                work_min=str(self.e_work.var.get()).strip() or None,
                short_min=str(self.e_short.var.get()).strip() or None,
                long_min=str(self.e_long.var.get()).strip() or None,
                rounds=str(self.e_rounds.var.get()).strip() or None)
            self._refresh()

        for f in (self.e_work, self.e_short, self.e_long, self.e_rounds):
            try:
                f.var.trace_add("write", _apply_settings)
            except Exception:
                pass

        def _apply_flags(*_):
            self.engine.auto_break = bool(self.c_auto_break.get())
            self.engine.auto_work = bool(self.c_auto_work.get())

        for c in (self.c_auto_break, self.c_auto_work):
            try:
                c.var.trace_add("write", _apply_flags)
            except Exception:
                pass

        # --- 3. сегодня ---
        s3 = Section(parent, "3. Сегодня",
                     subtitle="в полночь счётчики начинаются с нуля")
        self.lbl_done = ctk.CTkLabel(s3.inner, text="", font=FONT,
                                     anchor="w")
        self.lbl_done.pack(anchor="w")
        self.lbl_total = ctk.CTkLabel(s3.inner, text="", font=FONT,
                                      anchor="w")
        self.lbl_total.pack(anchor="w")
        row3 = button_row(s3.inner)
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
