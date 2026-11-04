"""Смоук-тест вкладки «Писателям» (05.11).

Собирает реальное окно (нужен дисплей: под Linux — Xvfb) и проверяет:
- вкладка «Писателям» существует и стоит первой;
- поля-инструменты живут на ней (f_ar, f_pc, f_style, f_stats, f_yo_input);
- на старых вкладках их больше нет (f_ar у CleanTab и т.д.);
- кнопки перенесённых инструментов вызывают нужные движки;
- журнал открывается по Ctrl+7.
Запуск: python test_gui_smoke.py  (Windows, с окном)
        xvfb-run -a python test_gui_smoke.py  (Linux, без дисплея)
Под pytest только импортируется: вся работа — в main().
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import importlib.util
from importlib.machinery import SourceFileLoader

failures = []


def check(name, cond, detail=""):
    print(("  ok  " if cond else "  FAIL ") + name
          + ("" if cond else f" :: {detail}"))
    if not cond:
        failures.append(name)


def main():
    loader = SourceFileLoader("gui_ctk", str(HERE / "gui_ctk.pyw"))
    spec = importlib.util.spec_from_loader("gui_ctk", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gui_ctk"] = mod
    loader.exec_module(mod)
    gui_ctk = mod

    app = gui_ctk.App()
    for _ in range(6):
        app.update()
        time.sleep(0.1)

    tabs = app._tabs
    check("вкладка «Писателям» есть", "Писателям" in tabs, str(list(tabs)))
    check("«Писателям» первая", list(tabs)[0] == "Писателям", str(list(tabs)))
    w = tabs["Писателям"]
    for attr in ("f_ar", "c_ar_fix", "f_pc", "f_pc_custom", "c_pc_dry",
                 "f_style", "e_style_window", "f_stats", "c_stats_csv",
                 "f_yo_input", "f_yo_reg"):
        check(f"поле {attr} на «Писателям»", hasattr(w, attr))

    clean = tabs["Чистка"]
    vault = tabs["Хранилище"]
    names = tabs["Имена персонажей"]
    check("у «Чистки» нет f_ar (переехала)", not hasattr(clean, "f_ar"))
    check("у «Хранилища» нет f_pc", not hasattr(vault, "f_pc"))
    check("у «Хранилища» нет f_stats", not hasattr(vault, "f_stats"))
    check("у «Хранилища» нет f_style", not hasattr(vault, "f_style"))
    check("у «Имён» нет f_yo_input", not hasattr(names, "f_yo_input"))

    # запуски идут в нужные движки
    calls = []
    gui_ctk.run_internal = lambda m, args: calls.append(
        ("internal", m, tuple(args)))
    gui_ctk.run_cmd = lambda cmd: calls.append(("cmd", tuple(cmd)))
    app.begin_run = lambda: True

    w.f_ar.set("C:/tmp/novel")
    w.c_ar_fix.var.set(True)
    w._run_ar()
    w.f_style.set("C:/tmp/novel")
    w.e_style_window.set("6")
    w._run_style()
    w.f_stats.set("C:/tmp/novel")
    w._run_stats()
    w.f_pc.set("C:/tmp/novel")
    w._run_phrase_check()

    check("АНТИРЕШИМОСТЬ → antiresolve --clean",
          ("internal", "antiresolve",
           ("--input", "C:/tmp/novel", "--clean")) in calls)
    check("стилистика → style_report с окном",
          any(c[0] == "internal" and c[1] == "style_report"
              and "--window" in c[2] for c in calls))
    check("статистика → text_stats",
          any(c[0] == "internal" and c[1] == "text_stats" for c in calls))
    check("штампы → phrase_check процессом",
          any(c[0] == "cmd" and any("phrase_check" in str(x) for x in c[1])
              for c in calls))

    # горячие клавиши: журнал — 7-я вкладка
    app.event_generate("<Control-Key-7>")
    app.update()
    check("Ctrl+7 → журнал",
          app._current_tab == gui_ctk.LOG_TAB, app._current_tab)
    app.event_generate("<Control-Key-1>")
    app.update()
    check("Ctrl+1 → «Писателям»",
          app._current_tab == "Писателям", app._current_tab)

    app.destroy()
    print()
    print("ИТОГ:", "все проверки зелёные" if not failures
          else f"ПРОВАЛЫ: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
