"""Ядро помодоро-таймера — вкладка «Помодоро».

18.11: бонус-фича по запросу владельца — трекер времени писателя по
технике Pomodoro. Техника: 25 минут сфокусированной работы, затем
5 минут короткого перерыва; после 4 помидоров подряд — длинный
перерыв 15 минут.

Логика фаз живёт здесь, без tkinter: её можно тестировать без дисплея
(test/test_pomodoro.py), а вкладка GUI (tabs_pomodoro.py) только
рисует состояние движка и кормит его тиками. Движок не знает ни про
конфиг, ни про журнал — он чистая машина состояний.

Если когда-нибудь появится CLI-режим (python textools.py pomodoro
--work 25), он переиспользует этот же класс.
"""

import time

WORK = "work"      # сфокусированная работа
SHORT = "short"    # короткий перерыв
LONG = "long"      # длинный перерыв (после серии)

PHASE_TITLES = {
    WORK: "Работа",
    SHORT: "Короткий перерыв",
    LONG: "Длинный перерыв",
}

# границы длительностей: минуты фазы и длина серии
LIMITS_MIN = (1, 240)
LIMITS_ROUNDS = (1, 12)

DEFAULTS = {"work_min": 25, "short_min": 5, "long_min": 15, "rounds": 4}

# пресеты таймера: классика и режим 50/10 владельца (22.11).
# Значения подставляются в поля «Настроек», движку менять нечего —
# это те же pomo.work_min/short_min/long_min/rounds.
PRESETS = {
    "25/5": {"work_min": 25, "short_min": 5, "long_min": 15, "rounds": 4},
    "50/10": {"work_min": 50, "short_min": 10, "long_min": 30, "rounds": 4},
}

DEFAULT_INTERRUPT_THRESHOLD_MIN = 5  # пауза в работе дольше — прерывание

# события журнала сессии: созвучно журналу DeepSeek (порция 2 ревью),
# но без сериализации — журнал живёт в памяти сессии
EV_START = "start"
EV_PAUSE = "pause"
EV_RESUME = "resume"
EV_INTERRUPT = "interrupt"
EV_NOTE = "note"
EV_WORK_END = "work_end"
EV_BREAK_END = "break_end"
EV_WORK_START = "work_start"
EV_BREAK_START = "break_start"
EV_FINISH = "finish"


def now_stamp():
    """Таймстамп журнала сессии: 'YYYY-MM-DD HH:MM:SS' локального
    времени (офлайн-приложение, локальный день читаемее UTC)."""
    return time.strftime("%Y-%m-%d %H:%M:%S")


def fmt_total(seconds):
    """Чистое время работы по-человечески: до часа «N мин», дальше
    «H ч M мин» (используется в отчёте сессии)."""
    m = max(0, int(seconds)) // 60
    if m < 60:
        return f"{m} мин"
    return f"{m // 60} ч {m % 60} мин"


def session_report_lines(rep):
    """Отчёт сессии строками для окна «Итог сессии» — формат из
    ревью (порции 1–2): задача, помидоры, время, отвлечения, журнал."""
    L = []
    if rep.get("task"):
        L.append(f"Задача: {rep['task']}")
    L.append(f"Помидоров выполнено: {rep.get('done_pomodoros', 0)}")
    L.append(f"Чистое время работы: {fmt_total(rep.get('work_seconds', 0))}")
    intr = rep.get("interruptions", [])
    L.append(f"Отвлечения: {', '.join(intr) if intr else '—'}")
    L.append("")
    L.append("Журнал сессии:")
    for j in rep.get("journal", []):
        note = f" — {j['note']}" if j.get("note") else ""
        L.append(f"  {j['ts']}  [{j['event']}]  "
                 f"{PHASE_TITLES.get(j.get('phase'), '')}{note}")
    return L


def clamp_min(value, default):
    """Длительность фазы в минутах: целое в границах LIMITS_MIN,
    иначе default. Пустая строка и мусор -> default (настройка просто
    не применится, а не уронит таймер)."""
    try:
        v = int(float(str(value).strip().replace(",", ".")))
    except (TypeError, ValueError):
        return int(default)
    return max(LIMITS_MIN[0], min(LIMITS_MIN[1], v))


def clamp_rounds(value, default):
    """Помидоров до длинного перерыва: целое в границах LIMITS_ROUNDS,
    иначе default."""
    try:
        v = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return int(default)
    return max(LIMITS_ROUNDS[0], min(LIMITS_ROUNDS[1], v))


def fmt_mmss(seconds):
    """MM:SS с двузначными полями; минуты не сворачиваются в часы,
    потому что максимальная фаза — 240 минут («240:00» читается лучше,
    чем «4:00:00» в крупном шрифте таймера)."""
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def ensure_day(stats, today):
    """Дневные счётчики с откатом на новую дату.

    stats — словарь из конфига (pomo.day / pomo.work_done /
    pomo.work_seconds), today — строка 'YYYY-MM-DD'. Возвращает
    словарь с ровно тремя ключами; если дата в stats не сегодняшняя —
    счётчики обнуляются (новый день — новый отсчёт)."""
    if not isinstance(stats, dict):
        stats = {}
    if stats.get("day") == today:
        try:
            done = max(0, int(stats.get("work_done", 0)))
        except (TypeError, ValueError):
            done = 0
        try:
            secs = max(0, int(stats.get("work_seconds", 0)))
        except (TypeError, ValueError):
            secs = 0
        return {"day": today, "work_done": done, "work_seconds": secs}
    return {"day": today, "work_done": 0, "work_seconds": 0}


class PomodoroEngine:
    """Машина фаз «работа -> короткий -> ... -> длинный перерыв».

    Управление: start() / pause() / toggle() / reset() / skip() /
    tick(seconds). tick возвращает список событий:
      ("phase_end", фаза)     — фаза досчитала до нуля;
      ("work_done", n)        — завершён n-й помидор в серии;
      ("phase_start", фаза)   — началась следующая фаза.
    Автостарт следующей фазы регулируют флаги auto_break / auto_work:
    по классике перерыв начинается сам (auto_break=True), а работу
    автор начинает вручную (auto_work=False)."""

    def __init__(self, work_min=DEFAULTS["work_min"],
                 short_min=DEFAULTS["short_min"],
                 long_min=DEFAULTS["long_min"],
                 rounds=DEFAULTS["rounds"],
                 auto_break=True, auto_work=False):
        self.rounds = clamp_rounds(rounds, DEFAULTS["rounds"])
        self._durations = {
            WORK: clamp_min(work_min, DEFAULTS["work_min"]) * 60,
            SHORT: clamp_min(short_min, DEFAULTS["short_min"]) * 60,
            LONG: clamp_min(long_min, DEFAULTS["long_min"]) * 60,
        }
        self.auto_break = bool(auto_break)
        self.auto_work = bool(auto_work)
        self.phase = WORK
        self.remaining = self._durations[WORK]
        self.running = False
        # завершённые помидоры с последнего длинного перерыва
        self._round_in_series = 0
        # всего завершённых помидоров за сессию (для итогового отчёта)
        self.session_done = 0
        # чистое время завершённых помидоров за сессию (для дневной
        # статистики GUI и будущего CLI-режима)
        self.done_work_seconds = 0
        # --- сессия (22.11, по материалу ревью DeepSeek): задача,
        # журнал, отвлечения, порог прерывания ---
        self.task = ""
        self.interrupt_threshold_min = DEFAULT_INTERRUPT_THRESHOLD_MIN
        self.journal = []      # [{"ts","event","phase","note"}]
        self.interruptions = []  # строки-причины, порядок сохранения
        self._pause_started = None  # time.monotonic() начала паузы
        self._pause_accum = 0.0     # накопленная пауза текущей фазы
        self._pause_counted = False  # прерывание уже записано за паузу

    # --- настройки ---

    def set_durations(self, work_min=None, short_min=None, long_min=None,
                      rounds=None):
        """Применить настройки. None и пустые строки = не менять. Новая
        длительность берёт следующая фаза; если таймер стоит в начале
        текущей (отсчёт не начат), отображение обновляется сразу —
        цифры на экране не противоречат настройкам. Пауза в середине
        фазы отсчёт не трогает: доигрывается старая длительность, как
        и после перезапуска программы (18.11: раньше любой ввод в
        поле настроек перезаряжал стоящий на паузе отсчёт)."""
        if rounds is not None:
            self.rounds = clamp_rounds(rounds, self.rounds)
        fresh = (not self.running
                 and self.remaining == self._durations[self.phase])
        changed_current = False
        for phase, val in ((WORK, work_min), (SHORT, short_min),
                           (LONG, long_min)):
            if val is None or str(val).strip() == "":
                continue
            mins = clamp_min(val, self._durations[phase] // 60)
            if mins * 60 == self._durations[phase]:
                continue          # значение не изменилось — не трогаем
            self._durations[phase] = mins * 60
            if phase == self.phase:
                changed_current = True
        if fresh and changed_current:
            self.remaining = self._durations[self.phase]

    def state(self):
        """Снимок состояния для отображения и тестов."""
        return {
            "phase": self.phase,
            "title": PHASE_TITLES[self.phase],
            "remaining": self.remaining,
            "running": self.running,
            "round_in_series": self._round_in_series,
            "rounds": self.rounds,
            "durations": dict(self._durations),
            "done_work_seconds": self.done_work_seconds,
        }

    # --- сессия: задача, журнал, отвлечения ---

    def set_task(self, task):
        """Назвать задачу цикла (правило «одна задача на цикл» из
        спецификации ревью). Попадает в журнал и итоговый отчёт."""
        self.task = str(task or "").strip()

    def _log(self, event, note=""):
        """Запись журнала сессии. Лишних строк не плодим: журнал —
        только значимые события (старт/пауза/фазы/отвлечения)."""
        self.journal.append({
            "ts": now_stamp(),
            "event": event,
            "phase": self.phase,
            "note": note,
        })

    def add_interruption(self, reason):
        """Кнопка «Отвлечение»: причина — в список отвлечений и в
        журнал (событие EV_INTERRUPT, note — причина)."""
        reason = str(reason or "").strip() or "без причины"
        self.interruptions.append(reason)
        self._log(EV_INTERRUPT, note=reason)

    def add_note(self, text):
        """Произвольная пометка в журнал сессии."""
        self._log(EV_NOTE, note=str(text or "").strip())

    def _count_interrupt_if_needed(self):
        """Правило из ревью: пауза в РАБОТЕ дольше порога (5 мин)
        — цикл считается прерванным: событие EV_INTERRUPT с note.
        Один раз на паузу; на перерывах порог не применяется."""
        if self._pause_started is None or self._pause_counted:
            return
        self._pause_counted = True
        secs = time.monotonic() - self._pause_started
        if (self.phase == WORK
                and secs >= self.interrupt_threshold_min * 60):
            self._log(EV_INTERRUPT, note="пауза %d мин — цикл прерван"
                      % max(1, int(secs // 60)))

    def start_session(self, task=""):
        """Новая сессия: задача, чистый журнал, чистые отвлечения,
        таймер в начало первой работы, отсчёт остановлен (старт —
        решает автор). Возвращает состояние."""
        self.set_task(task)
        self.journal = []
        self.interruptions = []
        self._pause_started = None
        self._pause_accum = 0.0
        self._pause_counted = False
        self.reset()
        self._log(EV_START, note=self.task)
        return self.state()

    def session_report(self):
        """Итоговый отчёт сессии (формат из ревью порций 1–2):
        задача, помидоры, чистое время работы, отвлечения, журнал."""
        return {
            "task": self.task,
            "done_pomodoros": self.session_done,
            "work_seconds": self.done_work_seconds,
            "interruptions": list(self.interruptions),
            "journal": list(self.journal),
        }

    def finish_session(self):
        """Завершить сессию: стоп, событие EV_FINISH, отчёт."""
        self.running = False
        if self._pause_started is not None:
            self._pause_accum += time.monotonic() - self._pause_started
            self._pause_started = None
        self._log(EV_FINISH)
        return self.session_report()

    # --- управление ---

    def start(self):
        if self._pause_started is not None:
            # возобновление: порог прерывания проверяется ДО сброса
            # таймера паузы (monotonic читается, пока пауза жива)
            self._count_interrupt_if_needed()
            self._pause_accum += time.monotonic() - self._pause_started
            self._pause_started = None
            self._log(EV_RESUME)
        else:
            self._pause_accum = 0.0
            self._pause_counted = False
            self._log(EV_START)
        self.running = True

    def pause(self):
        if self.running:
            self._pause_started = time.monotonic()
            self._log(EV_PAUSE)
        self.running = False

    def toggle(self):
        """Старт/пауза одним действием. Возвращает состояние running.
        Идёт через pause()/start(), чтобы пауза учитывалась порогом
        прерывания и журналом."""
        (self.pause if self.running else self.start)()
        return self.running

    def reset(self):
        """В начало текущей фазы, отсчёт остановлен."""
        self.running = False
        self.remaining = self._durations[self.phase]
        self._pause_started = None
        self._pause_accum = 0.0
        self._pause_counted = False

    def skip(self):
        """Перейти к следующей фазе сразу. Пропущенная работа в счёт
        помидоров не идёт — засчитывается только досчитанная фаза.
        Если таймер был на паузе, следующая фаза тоже стоит на старте:
        автостарт работает только от досчитанной фазы, а не от кнопки
        — когда садиться, решает автор (18.11). Пауза перед пропуском
        не перетекает в следующую фазу (22.11): иначе следующий
        «Старт» пишет в журнал resume вместо start, копит чужую
        паузу и проверяет порог прерывания уже за пределами той
        фазы, где пауза была."""
        was_running = self.running
        self._pause_started = None
        self._pause_accum = 0.0
        self._pause_counted = False
        events = [("phase_end", self.phase)]
        nxt = self._advance_phase()
        self.phase = nxt
        self.remaining = self._durations[nxt]
        self.running = self._auto_for(nxt) if was_running else False
        events.append(("phase_start", nxt))
        return events

    def tick(self, seconds=1):
        """Шаг отсчёта; вызывает GUI раз в секунду (или тест крупным
        шагом). На паузе событий нет. Возвращает список событий."""
        if not self.running:
            return []
        self.remaining -= max(1, int(seconds))
        if self.remaining > 0:
            return []
        events = [("phase_end", self.phase)]
        if self.phase == WORK:
            self._round_in_series += 1
            self.session_done += 1
            self.done_work_seconds += self._durations[WORK]
            events.append(("work_done", self._round_in_series))
            self._log(EV_WORK_END)
        else:
            self._log(EV_BREAK_END)
        nxt = self._advance_phase()
        self.phase = nxt
        self.remaining = self._durations[nxt]
        self.running = self._auto_for(nxt)
        if nxt in (SHORT, LONG):
            self._log(EV_BREAK_START)
        else:
            self._log(EV_WORK_START)
        events.append(("phase_start", nxt))
        return events

    # --- внутреннее ---

    def _advance_phase(self):
        """Какая фаза идёт следом за текущей. Вызывать ПОСЛЕ учёта
        завершённой работы (tick) — серия уже увеличена. Вызов из
        skip() честно переводит через ту же логику: пропуск помидора
        длинный перерыв не приближает."""
        if self.phase == WORK:
            return LONG if self._round_in_series >= self.rounds else SHORT
        if self.phase == LONG:
            # длинный перерыв закрывает серию
            self._round_in_series = 0
        return WORK

    def _auto_for(self, phase):
        return self.auto_break if phase in (SHORT, LONG) else self.auto_work
