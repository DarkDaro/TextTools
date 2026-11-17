"""Ядро помодоро-таймера — вкладка «Помодоро».

23.11: бонус-фича по запросу владельца — трекер времени писателя по
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
        # чистое время завершённых помидоров за сессию (для дневной
        # статистики GUI и будущего CLI-режима)
        self.done_work_seconds = 0

    # --- настройки ---

    def set_durations(self, work_min=None, short_min=None, long_min=None,
                      rounds=None):
        """Применить настройки. None = не менять. Новая длительность
        берёт следующая фаза; если таймер стоит в начале фазы
        (не запущен), отображение обновляется сразу — цифры на экране
        не противоречат настройкам."""
        if rounds is not None:
            self.rounds = clamp_rounds(rounds, self.rounds)
        for phase, val in ((WORK, work_min), (SHORT, short_min),
                           (LONG, long_min)):
            if val is None or str(val).strip() == "":
                continue
            mins = clamp_min(val, self._durations[phase] // 60)
            self._durations[phase] = mins * 60
        if not self.running:
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

    # --- управление ---

    def start(self):
        self.running = True

    def pause(self):
        self.running = False

    def toggle(self):
        """Старт/пауза одним действием. Возвращает состояние running."""
        self.running = not self.running
        return self.running

    def reset(self):
        """В начало текущей фазы, отсчёт остановлен."""
        self.running = False
        self.remaining = self._durations[self.phase]

    def skip(self):
        """Перейти к следующей фазе сразу. Пропущенная работа в счёт
        помидоров не идёт — засчитывается только досчитанная фаза."""
        events = [("phase_end", self.phase)]
        nxt = self._advance_phase()
        self.phase = nxt
        self.remaining = self._durations[nxt]
        self.running = self._auto_for(nxt)
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
            self.done_work_seconds += self._durations[WORK]
            events.append(("work_done", self._round_in_series))
        nxt = self._advance_phase()
        self.phase = nxt
        self.remaining = self._durations[nxt]
        self.running = self._auto_for(nxt)
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
