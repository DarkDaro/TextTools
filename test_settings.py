"""Автопроверка настроек GUI: кликабельность и применение.

Проверяет, что:
  1) каждая галочка и каждое поле вкладок пишут своё значение в конфиг;
  2) «Сохранить сейчас» записывает файл настроек;
  3) тема переключается и запоминается;
  4) у всех кнопок действий есть команда (кликабельность);
  5) поля на одном ключе конфига (md_vault) синхронизированы;
  6) история путей ограничена настройкой path_history_limit.

Запуск: python test_settings.py   (окно открывается, как в test_gui.py)
Выход: 0 — все проверки зелёные, 1 — есть провалы.
"""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gui_config  # noqa: E402
import widgets_ctk  # noqa: E402

CONFIG_FILE = HERE / "gui_config.json"


def _load_gui_ctk():
    """gui_ctk лежит .pyw-файлом — обычный import его не видит
    (.pyw есть в суффиксах исходников только на Windows)."""
    from importlib.machinery import SourceFileLoader
    path = str(HERE / "gui_ctk.pyw")
    loader = SourceFileLoader("gui_ctk", path)
    spec = importlib.util.spec_from_loader("gui_ctk", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gui_ctk"] = mod
    loader.exec_module(mod)
    return mod


def walk(w):
    yield w
    for c in w.winfo_children():
        yield from walk(c)


def main():
    gui_ctk = _load_gui_ctk()

    # сохранить настройки пользователя и вернуть их после проверки
    backup = (CONFIG_FILE.read_text(encoding="utf-8")
              if CONFIG_FILE.exists() else None)
    failures = []
    passed = 0

    def check(name, cond, detail=""):
        nonlocal passed
        if cond:
            passed += 1
            print(f"  ok  {name}")
        else:
            failures.append(name)
            print(f"  ПРОВАЛ: {name} {detail}")

    try:
        CONFIG_FILE.unlink(missing_ok=True)
        gui_config.reset()

        app = gui_ctk.App()
        app.update()

        # 1. каждая галочка/поле пишут в конфиг
        print("[1] автосохранение полей и галочек")
        seen = {}
        for tab in app._tabs.values():
            for w in walk(tab):
                if isinstance(w, (widgets_ctk.CheckField,
                                  widgets_ctk.EntryField,
                                  widgets_ctk.PathField)):
                    seen.setdefault(w.key, w)
        for key, field in sorted(seen.items()):
            if key == "gui.path_history":
                continue
            if isinstance(field, widgets_ctk.CheckField):
                # CheckField сохраняет по клику: var + _save
                new = not bool(field.get())
                field.var.set(new)
                field._save()
            else:
                cur = str(field.get() or "")
                new = cur + "_t" if not cur.endswith("_t") else cur[:-2]
                field.set(new)
            got = gui_config.CFG.get(key, None)
            check(f"ключ «{key}» пишется в конфиг", got == new,
                  f"(получено {got!r}, ждали {new!r})")

        # 2. «Сохранить сейчас» пишет файл
        print("[2] сохранение в файл")
        st = app._tabs.get("Настройки")
        if st is not None:
            st._save_now()
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            check("файл настроек содержит изменённые ключи",
                  data.get("show_cmd") == gui_config.CFG.get("show_cmd"))

        # 3. тема
        print("[3] тема")
        app._on_theme_change("light")
        check("тема переключается на light",
              "light" in str(__import__(
                  "customtkinter").get_appearance_mode()).lower())
        app._on_theme_change("dark")
        check("тема возвращается и пишется в конфиг",
              str(gui_config.CFG.get("theme")).lower() == "dark")

        # 4. кнопки
        print("[4] кликабельность кнопок")
        no_cmd = []
        total = 0
        for tab_name, tab in app._tabs.items():
            for w in walk(tab):
                if isinstance(w, widgets_ctk.ActionButton):
                    total += 1
                    cmd = w.cget("command")
                    if cmd is None or not callable(cmd):
                        no_cmd.append(f"{tab_name}:{w.cget('text')}")
        check(f"у всех {total} кнопок есть команда", not no_cmd, str(no_cmd))

        # 5. синхронизация полей на одном ключе
        print("[5] общие поля")
        rt = app._tabs.get("Замены")
        if rt is not None and hasattr(rt, "f_vault2"):
            rt.f_vault.set("/tmp/vault-A")
            app.update()
            check("второе поле vault видит путь из первого",
                  rt.f_vault2.get() == "/tmp/vault-A",
                  f"(второе показывает {rt.f_vault2.get()!r})")

        # 6. лимит истории путей
        print("[6] история путей")
        vt = app._tabs.get("Хранилище")
        if vt is not None:
            f = vt.f_vault
            limit = f._history_limit()
            for i in range(limit + 3):
                f._remember(f"/tmp/hist-{i:02d}")
            check(f"история ограничена {limit} записями",
                  len(f._history_list()) <= limit,
                  f"(хранится {len(f._history_list())})")

        app.destroy()
    finally:
        # вернуть настройки пользователя
        if backup is not None:
            CONFIG_FILE.write_text(backup, encoding="utf-8")
        else:
            CONFIG_FILE.unlink(missing_ok=True)
        gui_config.reset()

    print(f"\nИтого: ок {passed}, провал {len(failures)}")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
