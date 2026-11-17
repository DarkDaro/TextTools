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

from core.pomodoro import (DEFAULTS, LONG, SHORT, WORK, PomodoroEngine,
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
