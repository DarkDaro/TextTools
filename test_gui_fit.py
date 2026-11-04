"""Проверка умещения интерфейса (05.11).

Строит реальное окно (нужен дисплей: под Linux — Xvfb) при минимальном
размере 900x640 и проверяет, что при масштабе интерфейса 1.0 и 1.25:
- ни одна строка кнопок не требует ширины больше доступной;
- панель вкладок умещается.

Запуск: python test_gui_fit.py  (Windows, с окном)
        xvfb-run -a python test_gui_fit.py  (Linux, без дисплея)
Под pytest только импортируется: вся работа — в main().

История: при масштабе 1.25 вылезали три ряда («Хранилище», спецрежимы
«Замены», «О программе» в «Настройках») — кнопки обрезались краем окна.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

SCALES = (1.0, 1.25)
WIN_W = 900
CHROME = 72  # отступы: вкладки (32) + скролл (12) + карточка Section (28)


def _fit_for_scale(scale):
    """Строит окно при одном масштабе, возвращает список переливов."""
    import importlib.util
    import time
    from importlib.machinery import SourceFileLoader

    import customtkinter as ctk
    ctk.set_widget_scaling(scale)

    loader = SourceFileLoader("gui_ctk", str(HERE / "gui_ctk.pyw"))
    spec = importlib.util.spec_from_loader("gui_ctk", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gui_ctk"] = mod
    loader.exec_module(mod)

    from widgets_ctk import ActionButton  # noqa: E402

    app = mod.App()
    app.geometry(f"{WIN_W}x640+0+0")
    for _ in range(8):
        app.update()
        time.sleep(0.05)

    overflows = []

    seg = app.nb._segmented_button
    if seg.winfo_reqwidth() > WIN_W - 32:
        overflows.append(f"панель вкладок: {seg.winfo_reqwidth()}px")

    def walk(w):
        yield w
        for c in w.winfo_children():
            yield from walk(c)

    for tab_label, tab in app._tabs.items():
        if tab_label == "Журнал":
            continue
        for wdg in walk(tab):
            kids = wdg.winfo_children()
            btns = [k for k in kids if isinstance(k, ActionButton)]
            if len(btns) < 2:
                continue  # одиночные кнопки переносятся строкой ниже
            total = wdg.winfo_reqwidth() + CHROME
            if total > WIN_W:
                names = " + ".join(b.cget("text")[:24] for b in btns)
                overflows.append(f"[{tab_label}] {total}px: {names}")

    app.destroy()
    return overflows


def _run_child(scale):
    """Один масштаб — один процесс (два CTk-окна в одном процессе
    ненадёжны). Возвращает список переливов."""
    proc = subprocess.run(
        [sys.executable, __file__, "--measure", str(scale)],
        capture_output=True, text=True, timeout=300,
        env={**__import__("os").environ, "TT_FIT_CHILD": "1"})
    out = proc.stdout.strip().splitlines()
    if proc.returncode != 0 or not out:
        return [f"замер не удался: {proc.stderr.strip()[-200:]}"]
    return eval(out[-1])  # список строк из печатаемого списка


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--measure":
        print(_fit_for_scale(float(sys.argv[2])))
        return 0
    failures = []
    for scale in SCALES:
        overflows = _run_child(scale)
        print(f"  масштаб {scale}: переливов {len(overflows)}")
        for o in overflows:
            print(f"    FAIL {o}")
            failures.append(f"масштаб {scale}: {o}")
    if failures:
        print(f"\nИТОГ: НЕ умещается {len(failures)} ряд(ов)")
        return 1
    print("\nИТОГ: всё умещается")
    return 0


if __name__ == "__main__":
    sys.exit(main())
