"""Точечный тест вкладки «Помодоро» (18.11).

Собирает реальное окно (нужен дисплей: под Linux — Xvfb) и проверяет:
- вкладка «Помодоро» есть и стоит шестой (перед «Настройками»);
- кнопки таймера и счётчики дня на месте; полей длительностей у
  вкладки больше нет — настройки живут на «Настройках» (раздел
  «Помодоро», 18.11) и едут в движок мгновенно;
- правка длительности при стоящем таймере сразу видна на экране;
  мусор в поле даёт классические 25/5/15/4, как в подсказке;
- «Старт»/«Пауза» переключаются, «Сброс» возвращает полную фазу;
- короткая работа до нуля: помидор засчитан, статистика дня в конфиге,
  в журнале запись, фаза сменилась на перерыв;
- «Пропустить фазу» ведёт дальше без засчёта;
- «Обнулить счётчик» сбрасывает дневные числа, таймер не трогает;
- смена дня откатывает счётчики;
- Ctrl+6 ведёт на «Помодоро».
Конфиг пользователя восстанавливается байт-в-байт.

Запуск: DISPLAY=:77 python test_pomodoro_gui.py   (Linux, Xvfb)
        python test_pomodoro_gui.py               (Windows, с окном)
Под pytest только импортируется: вся работа — в main().
"""
import importlib.util
import json
import sys
import time
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gui_config
from gui_config import CONFIG_FILE

failures = []


def check(name, cond, detail=""):
    print(("  ok  " if cond else "  FAIL ") + name
          + ("" if cond else f" :: {detail}"))
    if not cond:
        failures.append(name)


def load_gui():
    loader = SourceFileLoader("gui_ctk", str(HERE / "gui_ctk.pyw"))
    spec = importlib.util.spec_from_loader("gui_ctk", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gui_ctk"] = mod
    loader.exec_module(mod)
    return mod


def pump(app, seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.02)


def main():
    backup = CONFIG_FILE.read_bytes() if CONFIG_FILE.exists() else None
    app = None
    try:
        gui_ctk = load_gui()
        from tabs_pomodoro import PomodoroTab

        # изолированный конфиг: как в test_settings — без старых значений
        CONFIG_FILE.unlink(missing_ok=True)
        gui_config.reset()

        app = gui_ctk.App()
        pump(app, 1.0)

        tabs = app._tabs
        check("вкладка «Помодоро» есть", "Помодоро" in tabs,
              str(list(tabs)))
        check("«Помодоро» шестая (перед «Настройками»)",
              list(tabs)[5] == "Помодоро", str(list(tabs)))
        p = tabs["Помодоро"]
        check("класс PomodoroTab", isinstance(p, PomodoroTab))
        for attr in ("engine", "b_start", "b_reset", "b_skip", "b_zero",
                     "lbl_time", "lbl_phase", "lbl_series",
                     "lbl_done", "lbl_total"):
            check(f"элемент {attr}", hasattr(p, attr))

        # настройки таймера — на «Настройках» (18.11), у самой вкладки
        # полей больше нет
        stt = app._tabs.get("Настройки")
        check("вкладка «Настройки» есть", stt is not None,
              str(list(app._tabs)))
        for attr in ("f_pomo_work", "f_pomo_short", "f_pomo_long",
                     "f_pomo_rounds", "c_pomo_auto_break",
                     "c_pomo_auto_work", "c_pomo_sound"):
            check(f"на «Настройках» есть {attr}", hasattr(stt, attr))
        check("у вкладки «Помодоро» нет своих полей настроек",
              not any(hasattr(p, a) for a in
                      ("e_work", "e_short", "e_long", "e_rounds",
                       "c_auto_break", "c_auto_work", "c_sound")))

        # движок получил классические настройки из пустого конфига
        st = p.engine.state()
        check("движок: классика 25/5/15, серия 4",
              st["durations"] == {"work": 1500, "short": 300, "long": 900}
              and st["rounds"] == 4, str(st))
        check("движок: фаза «Работа», стоит", st["phase"] == "work"
              and st["running"] is False, str(st))
        check("на экране 25:00", p.lbl_time.cget("text") == "25:00",
              p.lbl_time.cget("text"))

        # длительности едут из «Настроек» в конфиг и в движок мгновенно
        stt.f_pomo_work.set("3")
        pump(app, 1.0)
        check("поле «Работа» пишет в конфиг",
              str(gui_config.CFG.get("pomo.work_min")) == "3",
              str(gui_config.CFG.get("pomo.work_min")))
        check("движок применил 3 минуты (таймер стоит)",
              p.engine.state()["durations"]["work"] == 180,
              str(p.engine.state()["durations"]))
        check("на экране 03:00", p.lbl_time.cget("text") == "03:00",
              p.lbl_time.cget("text"))
        stt.f_pomo_work.set("abc")
        pump(app, 1.0)
        check("мусор в поле — классические 25 (как в подсказке)",
              p.engine.state()["durations"]["work"] == 1500,
              str(p.engine.state()["durations"]))
        check("на экране 25:00", p.lbl_time.cget("text") == "25:00",
              p.lbl_time.cget("text"))
        stt.f_pomo_work.set("1")
        pump(app, 1.0)
        check("на экране 01:00", p.lbl_time.cget("text") == "01:00",
              p.lbl_time.cget("text"))

        # галочка автостарта связана с движком через «Настройки»
        stt.c_pomo_auto_break.var.set(False)
        stt.c_pomo_auto_break._save()
        pump(app, 1.0)
        check("галочка «авто-перерыв» связана с движком",
              p.engine.auto_break is False, str(p.engine.auto_break))
        stt.c_pomo_auto_break.var.set(True)
        stt.c_pomo_auto_break._save()
        pump(app, 1.0)

        # старт / пауза / сброс
        p.b_start.invoke()
        pump(app, 0.2)
        check("«Старт» запустил отсчёт", p.engine.running is True)
        check("кнопка стала «Пауза»",
              p.b_start.cget("text") == "Пауза", p.b_start.cget("text"))
        p.engine.tick(10)
        p.b_start.invoke()
        pump(app, 0.2)
        check("«Пауза» остановила", p.engine.running is False
              and p.engine.remaining < 60)
        p.b_reset.invoke()
        pump(app, 0.2)
        check("«Сброс» вернул полную фазу и остановил",
              p.engine.remaining == 60 and p.engine.running is False)

        # короткая работа до нуля: помидор засчитан, перерыв начался
        log_before = len(app._log_panel.get_text())
        p.b_start.invoke()
        p.engine.tick(59)               # форвард: до конца фазы 1 секунда
        deadline = time.time() + 8
        while time.time() < deadline:
            pump(app, 0.4)
            if p.engine.phase == "short":
                break
        check("фаза сменилась на короткий перерыв",
              p.engine.phase == "short", p.engine.phase)
        check("перерыв стартовал сам (auto_break)",
              p.engine.running is True)
        stats = gui_config.CFG.get("pomo.stats", {})
        check("статистика дня: 1 помидор, 60 с",
              stats.get("work_done") == 1
              and stats.get("work_seconds") == 60, str(stats))
        check("на экране «Помидоров сегодня: 1»",
              "1" in p.lbl_done.cget("text"), p.lbl_done.cget("text"))
        check("в журнале запись о засчитанном помидоре",
              len(app._log_panel.get_text()) > log_before
              and "засчитан" in app._log_panel.get_text())
        # пауза перерыва, чтобы не тикал до конца теста
        p.engine.pause()

        # пропуск фазы
        log_before = len(app._log_panel.get_text())
        p.b_skip.invoke()
        pump(app, 0.2)
        check("«Пропустить фазу» ведёт на работу",
              p.engine.phase == "work", p.engine.phase)
        check("пропуск не засчитан: счётчик дня не вырос",
              gui_config.CFG.get("pomo.stats", {}).get("work_done") == 1,
              str(gui_config.CFG.get("pomo.stats")))
        check("пропуск записан в журнал",
              len(app._log_panel.get_text()) > log_before)

        # обнуление счётчика
        p.b_zero.invoke()
        pump(app, 0.2)
        stats = gui_config.CFG.get("pomo.stats", {})
        check("«Обнулить счётчик» сбросил день",
              stats.get("work_done") == 0 and stats.get("work_seconds") == 0,
              str(stats))
        check("таймер при обнулении не тронут",
              p.engine.phase == "work", p.engine.phase)

        # смена дня откатывает счётчики
        p._stats["work_done"] = 5
        p._stats["day"] = "2000-01-01"
        p._pump_day()
        check("новый день — счётчики в ноль",
              p._stats.get("work_done") == 0 and p._stats["day"] != "2000-01-01",
              str(p._stats))

        # горячая клавиша: «Помодоро» — шестая вкладка
        app._goto_tab("Писателям")
        app.update()
        app.event_generate("<Control-Key-6>")
        app.update()
        check("Ctrl+6 → «Помодоро»",
              app._current_tab == "Помодоро", app._current_tab)

        app.destroy()
    except Exception as e:
        import traceback
        traceback.print_exc()
        check("тест не упал с исключением", False, repr(e))
    finally:
        if backup is not None:
            CONFIG_FILE.write_bytes(backup)
        elif CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass

    print()
    print("ИТОГ:", "все проверки зелёные" if not failures
          else f"ПРОВАЛЫ: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
