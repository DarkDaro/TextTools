"""Тесты ядра помодоро-таймера (core/pomodoro.py).

Движок — чистая машина состояний без tkinter, поэтому вся логика
фаз проверяется здесь, без дисплея. Вкладка GUI проверяется отдельно
(test_pomodoro_gui.py, корень репо, нужен Xvfb).

Запуск:  python -m pytest test/test_pomodoro.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from core.pomodoro import (DEFAULTS, EV_PAUSE, EV_RESUME, EV_START, LONG,
                           SHORT, WORK, PomodoroEngine,
                           clamp_min, clamp_rounds, ensure_day, fmt_mmss)


def make_engine(**kw):
    """Движок с короткими фазами: удобно гонять цикл тиками по 1 с."""
    base = dict(work_min=1, short_min=1, long_min=1, rounds=2)
    base.update(kw)
    return PomodoroEngine(**base)


def cycle_work(engine, seconds=60):
    """Тикает до конца рабочей фазы, возвращает события."""
    events = []
    for _ in range(seconds):
        ev = engine.tick(1)
        if ev:
            events.append(ev)
    return events


# --- дефолты и отображение ------------------------------------------------

def test_defaults_classic_pomodoro():
    e = PomodoroEngine()
    st = e.state()
    assert st["phase"] == WORK
    assert st["remaining"] == 25 * 60
    assert st["durations"] == {WORK: 1500, SHORT: 300, LONG: 900}
    assert st["rounds"] == 4
    assert st["running"] is False
    assert st["title"] == "Работа"


def test_fmt_mmss():
    assert fmt_mmss(0) == "00:00"
    assert fmt_mmss(65) == "01:05"
    assert fmt_mmss(25 * 60) == "25:00"
    assert fmt_mmss(240 * 60) == "240:00"
    assert fmt_mmss(-5) == "00:00"  # защита от отрицательных


# --- тики и пауза ----------------------------------------------------------

def test_tick_decrements_only_while_running():
    e = make_engine()
    assert e.tick(10) == []          # не запущен — событий нет
    assert e.remaining == 60         # и отсчёт не трогается
    e.start()
    assert e.tick(10) == []
    assert e.remaining == 50
    e.pause()
    assert e.tick(10) == []
    assert e.remaining == 50


def test_toggle_returns_state():
    e = make_engine()
    assert e.toggle() is True
    assert e.running is True
    assert e.toggle() is False
    assert e.running is False


def test_reset_returns_to_full_phase_and_stops():
    e = make_engine()
    e.start()
    e.tick(20)
    e.reset()
    st = e.state()
    assert st["remaining"] == 60
    assert st["running"] is False
    assert st["phase"] == WORK


# --- цикл фаз ---------------------------------------------------------------

def test_work_done_leads_to_short_break_auto_start():
    e = make_engine()                 # auto_break=True по умолчанию
    e.start()
    flat = [ev for s in range(60) for ev in e.tick(1)]
    assert ("phase_end", WORK) in flat
    assert ("work_done", 1) in flat
    assert ("phase_start", SHORT) in flat
    st = e.state()
    assert st["phase"] == SHORT
    assert st["remaining"] == 60
    assert st["running"] is True      # перерыв начался сам


def test_long_break_after_series():
    e = make_engine(rounds=2)
    e.start()
    # первый помидор -> короткий перерыв -> второй помидор -> длинный
    for _ in range(60):
        e.tick(1)
    assert e.phase == SHORT
    for _ in range(60):
        e.tick(1)
    assert e.phase == WORK            # перерыв закончился, работа ждёт автора
    e.start()
    for _ in range(60):
        e.tick(1)
    st = e.state()
    assert st["phase"] == LONG        # после 2-го помидора — длинный
    assert st["round_in_series"] == 2
    assert st["running"] is True


def test_series_resets_after_long_break():
    e = make_engine(rounds=2)
    e.start()
    cycle_work(e)                     # помидор 1 -> SHORT (идёт сам)
    cycle_work(e)                     # SHORT кончился -> WORK (пауза)
    e.start()
    cycle_work(e)                     # помидор 2 -> LONG (идёт сам)
    assert e.phase == LONG
    e.skip()                          # пропускаем длинный перерыв
    st = e.state()
    assert st["phase"] == WORK
    assert st["round_in_series"] == 0  # серия закрыта
    # следующий помидор снова ведёт к короткому перерыву
    e.start()
    cycle_work(e)
    assert e.phase == SHORT


def test_break_end_waits_for_author_when_auto_work_off():
    e = make_engine()
    e.start()
    cycle_work(e)                     # работа -> перерыв (сам)
    assert e.running is True
    cycle_work(e)                     # перерыв досчитал -> работа
    assert e.phase == WORK
    assert e.running is False         # автостарта работы нет — ждём «Старт»


def test_auto_work_starts_work_by_itself():
    e = make_engine(auto_work=True)
    e.start()
    cycle_work(e)
    cycle_work(e)                     # перерыв закончился
    assert e.phase == WORK
    assert e.running is True


def test_done_work_seconds_accumulates():
    e = make_engine()
    e.start()
    cycle_work(e)                     # помидор засчитан
    assert e.done_work_seconds == 60
    cycle_work(e)                     # перерыв досчитал — время не растёт
    assert e.done_work_seconds == 60
    e.start()
    cycle_work(e)                     # второй помидор
    assert e.done_work_seconds == 120
    assert e.state()["done_work_seconds"] == 120


def test_skip_moves_on_without_counting():
    e = make_engine(rounds=2)
    e.start()
    e.tick(30)                        # полфазы
    ev = e.skip()
    assert ("phase_start", SHORT) in ev
    st = e.state()
    assert st["phase"] == SHORT
    assert st["remaining"] == 60
    assert st["round_in_series"] == 0  # пропущенная работа не считается
    assert st["running"] is True       # перерыв стартовал сам


def test_skip_long_break_closes_series():
    e = make_engine(rounds=1)
    e.start()
    cycle_work(e)                     # сразу длинный перерыв
    assert e.phase == LONG
    e.skip()
    assert e.phase == WORK
    assert e.state()["round_in_series"] == 0


# --- настройки ---------------------------------------------------------------

def test_set_durations_updates_display_when_idle():
    e = make_engine()
    e.set_durations(work_min=50)
    assert e.state()["remaining"] == 50 * 60
    e.set_durations(short_min=10, long_min=30, rounds=6)
    st = e.state()
    assert st["durations"][SHORT] == 600
    assert st["durations"][LONG] == 1800
    assert st["rounds"] == 6


def test_set_durations_running_does_not_touch_current_countdown():
    e = make_engine()
    e.start()
    e.tick(40)                        # осталось 20 с
    e.set_durations(work_min=50)
    assert e.remaining == 20          # текущая фаза не перезаряжается
    assert e.state()["durations"][WORK] == 3000  # следующая фаза — 50 мин


def test_empty_string_setting_is_ignored():
    e = make_engine()
    e.set_durations(work_min="   ")
    assert e.state()["durations"][WORK] == 60


def test_set_durations_paused_midphase_keeps_remaining():
    """18.11: пауза в середине фазы — настройки едут в следующую
    фазу, отсчёт не перезаряжается."""
    e = make_engine()
    e.start()
    e.tick(40)
    e.pause()
    e.set_durations(work_min=50, short_min=10, long_min=30, rounds=6)
    assert e.remaining == 20
    st = e.state()
    assert st["durations"][WORK] == 3000
    assert st["rounds"] == 6


def test_set_durations_same_value_keeps_paused_remaining():
    """18.11: повторная установка тех же значений (каждый ввод в поле
    даёт трейс) не перезаряжает стоящий на паузе отсчёт."""
    e = make_engine()
    e.start()
    e.tick(40)
    e.pause()
    e.set_durations(work_min=1, short_min=1, long_min=1, rounds=2)
    assert e.remaining == 20


def test_set_durations_fresh_phase_updates_display():
    """Таймер стоит в начале фазы — новая длительность видна сразу;
    чужая фаза отсчёт не трогает."""
    e = make_engine()
    e.set_durations(work_min=50)
    assert e.remaining == 50 * 60
    e.start()
    e.tick(30)
    e.pause()
    e.reset()
    assert e.remaining == 50 * 60
    e.set_durations(short_min=10)
    assert e.remaining == 50 * 60
    e.set_durations(work_min=30)
    assert e.remaining == 30 * 60


def test_skip_while_paused_stays_paused():
    """18.11: пропуск с паузы не включает автостарт — следующая фаза
    ждёт «Старт»."""
    e = make_engine()
    e.start()
    e.tick(30)
    e.pause()
    e.skip()
    assert e.phase == SHORT
    assert e.running is False
    assert e.remaining == 60
    e.start()
    assert e.running is True


# --- границы ------------------------------------------------------------------

def test_clamp_min_bounds_and_garbage():
    assert clamp_min(0, 25) == 1
    assert clamp_min(1000, 25) == 240
    assert clamp_min("40", 25) == 40
    assert clamp_min("40,5", 25) == 40
    assert clamp_min("", 25) == 25
    assert clamp_min("абв", 25) == 25
    assert clamp_min(None, 25) == 25


def test_clamp_rounds_bounds_and_garbage():
    assert clamp_rounds(0, 4) == 1
    assert clamp_rounds(99, 4) == 12
    assert clamp_rounds("6", 4) == 6
    assert clamp_rounds("много", 4) == 4
    assert clamp_rounds(None, 4) == 4


def test_defaults_are_classic():
    assert DEFAULTS == {"work_min": 25, "short_min": 5, "long_min": 15,
                        "rounds": 4}


# --- дневные счётчики ----------------------------------------------------------

def test_ensure_day_same_date_keeps_counters():
    stats = {"day": "2026-11-23", "work_done": 3, "work_seconds": 4500}
    out = ensure_day(stats, "2026-11-23")
    assert out == {"day": "2026-11-23", "work_done": 3,
                   "work_seconds": 4500}


def test_ensure_day_new_date_resets():
    stats = {"day": "2026-11-22", "work_done": 7, "work_seconds": 10500}
    out = ensure_day(stats, "2026-11-23")
    assert out == {"day": "2026-11-23", "work_done": 0, "work_seconds": 0}


def test_ensure_day_garbage_is_safe():
    assert ensure_day(None, "2026-11-23")["work_done"] == 0
    assert ensure_day({}, "2026-11-23")["work_done"] == 0
    bad = {"day": "2026-11-23", "work_done": "много", "work_seconds": None}
    out = ensure_day(bad, "2026-11-23")
    assert out["work_done"] == 0 and out["work_seconds"] == 0


# --- сессия: задача, журнал, отвлечения, порог (22.11, ревью) --------------

def test_presets_defined():
    # пресеты: классика и режим 50/10 (22.11)
    from core.pomodoro import PRESETS
    assert PRESETS["25/5"] == {"work_min": 25, "short_min": 5,
                               "long_min": 15, "rounds": 4}
    assert PRESETS["50/10"] == {"work_min": 50, "short_min": 10,
                                "long_min": 30, "rounds": 4}


def test_set_task_strips_and_tolerates_none():
    e = make_engine()
    e.set_task("  Ревью главы 3  ")
    assert e.task == "Ревью главы 3"
    e.set_task(None)
    assert e.task == ""
    e.set_task("   ")
    assert e.task == ""


def test_start_session_clears_and_logs():
    e = make_engine()
    e.set_task("старая задача")
    e.add_interruption("почта")
    e.start_session("Новая глава")
    assert e.task == "Новая глава"
    assert e.interruptions == []
    assert [j["event"] for j in e.journal] == ["start"]
    assert e.journal[0]["note"] == "Новая глава"
    assert e.running is False
    assert e.remaining == e._durations[WORK]


def test_journal_records_phases_and_counts():
    e = make_engine(work_min=1, short_min=1, long_min=1, rounds=1)
    e.start_session("глава")
    e.start()
    cycle_work(e)
    events = [j["event"] for j in e.journal]
    assert events[0] == "start"
    assert "work_end" in events
    assert "break_start" in events
    assert e.session_done == 1


def test_add_interruption_goes_to_both_places():
    e = make_engine()
    e.start_session()
    e.add_interruption("звонок")
    e.add_interruption("")  # пустая причина -> «без причины»
    assert e.interruptions == ["звонок", "без причины"]
    intr = [j for j in e.journal if j["event"] == "interrupt"]
    assert [j["note"] for j in intr] == ["звонок", "без причины"]


def test_short_pause_in_work_is_not_interrupt():
    e = make_engine()
    e.start_session("задача")
    e.start()
    e.pause()               # пауза короче порога
    e.start()
    assert e.interruptions == []
    assert not any(j["event"] == "interrupt" for j in e.journal)
    assert any(j["event"] == "pause" for j in e.journal)
    assert any(j["event"] == "resume" for j in e.journal)


def test_long_pause_in_work_counts_interrupt(monkeypatch):
    t = {"v": 100.0}
    monkeypatch.setattr("core.pomodoro.time.monotonic",
                        lambda: t["v"])
    e = make_engine()
    e.start_session("задача")
    e.start()
    e.pause()          # t=100
    t["v"] += 6 * 60   # пауза длилась 6 минут — больше порога в 5
    e.start()
    assert e.interruptions == []  # в списке отвлечений нет: пауза не кнопка
    intr = [j for j in e.journal if j["event"] == "interrupt"]
    assert len(intr) == 1
    assert "цикл прерван" in intr[0]["note"]


def test_interrupt_threshold_not_applied_to_breaks():
    e = make_engine(work_min=1, short_min=1, rounds=2)
    e.start_session()
    e.start()
    cycle_work(e)          # работа закончилась, начался перерыв
    e.pause()              # «долгая пауза», но фаза — перерыв
    e.start()
    assert not any(j["event"] == "interrupt" for j in e.journal)


def test_pause_on_stopped_engine_no_duplicates():
    e = make_engine()
    e.pause()              # таймер и так стоит — событий нет
    e.pause()
    assert not any(j["event"] == "pause" for j in e.journal)


def test_finish_session_report():
    e = make_engine(work_min=1, short_min=1, long_min=1, rounds=2)
    e.start_session("Ревью PR #142")
    e.start()
    cycle_work(e)          # 1 помидор
    rep = e.finish_session()
    assert rep["task"] == "Ревью PR #142"
    assert rep["done_pomodoros"] == 1
    assert rep["work_seconds"] == 60
    assert rep["interruptions"] == []
    assert [j["event"] for j in rep["journal"]][-1] == "finish"
    assert e.running is False


def test_skip_does_not_count_toward_session_done():
    e = make_engine()
    e.start_session()
    e.start()
    e.skip()               # работа пропущена — помидор не засчитан
    assert e.session_done == 0


def test_skip_from_pause_does_not_leak_pause_state():
    """22.11: пауза перед «Пропустить фазу» не перетекает в следующую
    фазу — иначе «Старт» в новой фазе писал бы в журнал resume вместо
    start и проверял бы порог прерывания не в той фазе."""
    e = make_engine()
    e.start_session()
    e.start()
    e.pause()
    e.skip()               # пауза -> SHORT, отсчёт стоит
    assert e.phase == SHORT
    e.start()
    events = [j["event"] for j in e.journal]
    assert events[-1] == EV_START   # resume после пропуска — ошибка
    assert e.running is True


def test_pause_threshold_not_checked_in_break_phase():
    """Порог прерывания (5 мин) действует только в РАБОТЕ: длинная
    пауза на перерыве — не отвлечение."""
    e = make_engine(work_min=1, short_min=1)
    e.start_session()
    e.start()
    e.tick(60)             # работа -> короткий перерыв
    e.pause()
    e.interrupt_threshold_min = 0  # порог = 0 с: пауза любой длины
    e.start()              # пауза короткая, но порог нулевой
    e.interrupt_threshold_min = 5
    e.pause()
    e.interrupt_threshold_min = 0
    e.start()
    assert [i for i in e.interruptions] == []
    assert all(j["event"] != "interrupt" for j in e.journal)
