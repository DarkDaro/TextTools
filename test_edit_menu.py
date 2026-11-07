"""Точечный тест EditMenu (07.11, редизайн GUI).

Проверяет: правый клик в полях ввода и в журнале, полный набор
правок (вырезать/копировать/вставить/выделить всё), Ctrl+C и Ctrl+A
в выключенном тексте журнала, подсветка рамки при фокусе.
Запуск: DISPLAY=:77 python test_edit_menu.py (нужен дисплей).
"""
import importlib.util
import os
import sys
import time
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

failures = []


def check(name, cond, detail=""):
    print(("  ok  " if cond else "  FAIL ") + name
          + ("" if cond else f" :: {detail}"))
    if not cond:
        failures.append(name)


def load_gui_ctk():
    loader = SourceFileLoader("gui_ctk", str(HERE / "gui_ctk.pyw"))
    spec = importlib.util.spec_from_loader("gui_ctk", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gui_ctk"] = mod
    loader.exec_module(mod)
    return mod


gui_ctk = load_gui_ctk()


def main():
    app = gui_ctk.App()
    try:
        for _ in range(5):
            app.update()
            time.sleep(0.1)

        from widgets_ctk import _edit_base

        print("[1] поля ввода: меню и правый клик")
        repl = app._tabs["Замены"]
        entry = repl.f_old.entry
        menu = getattr(repl.f_old, "_clip_menu", None)
        check("правый клик привязан к полю",
              bool(str(entry.bind("<Button-3>")).strip()))
        check("меню правки создано и имеет 6 пунктов",
              menu is not None and menu.index("end") == 5,
              str(menu.index("end") if menu else None))
        base = _edit_base(entry)
        base.delete(0, "end")
        base.insert(0, "старое имя")
        base.focus_set()
        app.update()
        # пункты меню: 0 Вырезать, 1 Копировать, 2 Вставить, 4 Выделить всё
        app.clipboard_clear()
        app.clipboard_append("новое имя")
        base.select_range(0, "end")
        menu.invoke(2)  # Вставить из буфера
        app.update()
        check("вставка из меню заменяет выделенное",
              entry.get() == "новое имя", entry.get())
        base.select_range(0, 5)
        menu.invoke(0)  # Вырезать
        app.update()
        check("вырезка из меню удаляет выделенное", entry.get() == " имя",
              repr(entry.get()))
        clip = ""
        try:
            clip = app.clipboard_get()
        except Exception:
            pass
        check("вырезанное попало в буфер", clip == "новое", repr(clip))
        menu.invoke(4)  # Выделить всё
        app.update()
        sel = ""
        try:
            # tk.Entry.get() индексы не принимает — только через selection_*
            if base.selection_present():
                sel = base.selection_get()
        except Exception:
            pass
        check("«Выделить всё» выделяет всё поле", sel == " имя", repr(sel))

        print("[2] журнал: правый клик и клавиатура копирования")
        log = app._log_panel
        app._goto_tab(gui_ctk.LOG_TAB)
        app.update()
        check("правый клик привязан к журналу",
              bool(str(log.text.bind("<Button-3>")).strip()))
        log.clear()
        log.append("строка для копирования\n")
        app.update()
        tbase = _edit_base(log.text)
        tbase.focus_set()
        tbase.tag_add("sel", "1.0", "end-1c")
        app.update()
        tbase.event_generate("<Control-c>")
        app.update()
        clip = ""
        try:
            clip = app.clipboard_get()
        except Exception:
            pass
        check("Ctrl+C копирует из выключенного журнала",
              "строка для копирования" in clip, repr(clip[:40]))
        tbase.event_generate("<Control-a>")
        app.update()
        sel = tbase.tag_ranges("sel")
        check("Ctrl+A выделяет весь журнал", bool(sel))
        app.clipboard_clear()
        log.copy_all()
        check("кнопка «Копировать всё» работает",
              "строка для копирования" in app.clipboard_get())

        print("[3] подсветка поля при фокусе")
        from widgets_ctk import ACCENT_FOCUS, ENTRY_BORDER
        f = repl.f_new.entry
        fb = _edit_base(f)
        # В Xvfb нет оконного менеджера — реальный фокус окну не даётся
        # (focus_get() == None), поэтому события фокуса генерируем явно:
        # привязка вешается на внутренний tk.Entry, как и в живом окне.
        fb.event_generate("<FocusIn>")
        app.update()
        check("при фокусе рамка акцентная",
              f.cget("border_color") == ACCENT_FOCUS,
              str(f.cget("border_color")))
        fb.event_generate("<FocusOut>")
        app.update()
        check("после потери фокуса рамка спокойная",
              f.cget("border_color") == ENTRY_BORDER,
              str(f.cget("border_color")))

        print("[4] история ▾ и «…» не сломались")
        vault = app._tabs["Хранилище"]
        field = vault_tab = vault.f_vault
        field._remember("C:/tmp/menu_test")
        check("история путей пишется",
              field._history_list()[0] == "C:/tmp/menu_test",
              str(field._history_list()[:1]))
    except Exception:
        import traceback
        traceback.print_exc()
        failures.append("исключение")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    print()
    if failures:
        print(f"ПРОВАЛ: {len(failures)}")
        for f in failures:
            print("  -", f)
        return 1
    print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
