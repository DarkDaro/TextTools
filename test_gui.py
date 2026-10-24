"""Автотест интерфейса textools (24.10, UI_DESIGN.md, раздел 10).

Проверяет: у каждой кнопки есть обработчик, безопасные кнопки реально
кликаются (запуск инструментов подменён заглушкой), вкладки и горячие
клавиши синхронизированы, история путей, журнал (поиск, очистка,
масштаб), тосты. Конфиг пользователя восстанавливается байт-в-байт.

Запуск: py -3.14 test_gui.py
"""
import sys
import tempfile
import time
import traceback
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import customtkinter as ctk

import gui_config
import gui_ctk

CONFIG = HERE / "gui_config.json"

# 24.10: кнопки, которые запускают инструменты. Кликаем их, подменив
# run_internal/run_cmd — реальные процессы и запись файлов не нужны.
RUN_BUTTONS = {
    "Найти кандидатов", "Проверить имена", "Построить матрицу",
    "Показать недостающие падежи", "Добавить кандидатов в реестр",
    "MOC-заметки персонажей", "Построить статистику",
    "Построить стилистический отчёт", "Orphans (одиночки)",
    "Битые ссылки", "Дубликаты (merge)", "Целостность", "Найти штампы",
    "Проверить заметки", "Найти иероглифы",
    "Почистить штампы", "Запустить чистку эмодзи",
    "Запустить чистку мусора", "Запустить чистку пробелов",
    "Проверить кодировки", "Запустить типографику", "Заменить",
    "Найти проблемные символы", "Починить UTF-8", "Вырезать мусор",
    "Проверить", "Заменить слово", "Запустить", "Проверить пути",
    "Показать / восстановить бэкапы",
    "Показать старые бэкапы / Архивировать", "Сохранить сейчас",
}

# 24.10: служебные кнопки без запуска инструментов: кликаем и смотрим,
# что действие отработало без исключения (лог вырос).
UTILITY_BUTTONS = {"Проверить пути", "Сохранить сейчас",
                   "Проверить зависимости", "Скопировать сведения",
                   "Найти скрипты"}

# 24.10: опасные (запись/удаление/внешние программы) — только привязка
# обработчика, без клика
SKIP_BUTTONS = {
    "Сбросить всё", "Открыть конфиг", "Открыть журнал",
    "Открыть папку отчётов", "Открыть список паразитов",
    "Открыть инструкцию", "Сбросить размер окна", "Ё/Е-аудит (витрина)",
    "Стоп", "Отчёт", "...", "▾", "Файл", "Сброс", "Очистить",
    "Копировать всё", "Найти",
}

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok  {name}")
    else:
        failures.append(f"{name}: {detail}")
        print(f"  FAIL {name} {detail}")


def collect_buttons(w):
    if isinstance(w, ctk.CTkButton):
        yield w
    for child in w.winfo_children():
        yield from collect_buttons(child)


def main():
    global _config_bytes
    _config_bytes = CONFIG.read_bytes() if CONFIG.exists() else None
    app = None
    try:
        app = gui_ctk.App()
        for _ in range(6):
            app.update()
            time.sleep(0.15)

        print("[1] кнопки")
        buttons = list(collect_buttons(app))
        check("кнопки найдены", len(buttons) > 40, f"всего {len(buttons)}")
        unbound = [b.cget("text") for b in buttons
                   if b.cget("command") is None]
        check("у всех кнопок есть command", not unbound, str(unbound[:5]))

        print("[2] клики безопасных кнопок")
        calls = []
        orig_internal = gui_ctk.run_internal
        orig_cmd = gui_ctk.run_cmd
        orig_begin = app.begin_run

        def fake_internal(mod, args):
            calls.append(("internal", mod, tuple(args)))

        def fake_cmd(cmd):
            calls.append(("cmd", tuple(cmd)))

        gui_ctk.run_internal = fake_internal
        gui_ctk.run_cmd = fake_cmd
        app.begin_run = lambda: True
        skipped = set()
        try:
            for b in buttons:
                text = b.cget("text")
                if text in RUN_BUTTONS or text in UTILITY_BUTTONS:
                    before = len(calls)
                    log_before = len(app._log_panel.get_text())
                    try:
                        b.invoke()
                        app.update()
                        # запуск мог не состояться из-за незаполненного
                        # поля — тогда в журнале появляется подсказка
                        started = len(calls) > before
                        logged = len(app._log_panel.get_text()) > log_before
                        check(f"клик «{text}»", started or logged,
                              "ни запуска, ни сообщения")
                    except Exception as e:
                        check(f"клик «{text}»", False, repr(e))
                elif text in SKIP_BUTTONS:
                    if text not in skipped:
                        skipped.add(text)
                        check(f"опасная «{text}» только с обработчиком",
                              b.cget("command") is not None)
        finally:
            gui_ctk.run_internal = orig_internal
            gui_ctk.run_cmd = orig_cmd
            app.begin_run = orig_begin

        char_calls = [c for c in calls if c[0] == "cmd"
                      and any("char_search" in str(x) for x in c[1])]
        check("«все» не уходит как имя персонажа",
              bool(char_calls) and all("все" not in c[1] for c in char_calls),
              str(char_calls[:1]))

        # 24.10: кнопка реальной записи краснеет по галочке «Применить»
        repl = app._tabs["Замены"]
        b_md = next(b for b in buttons if b.cget("text") == "Заменить")
        repl.c_apply.var.set(False)
        app.update()
        calm = b_md.cget("fg_color")
        repl.c_apply.var.set(True)
        app.update()
        hot = b_md.cget("fg_color")
        check("кнопка записи краснеет по галочке", calm != hot,
              f"{calm} -> {hot}")
        repl.c_apply.var.set(False)

        print("[3] вкладки и индикатор")
        for label in app._tabs:
            app._goto_tab(label)
            app.update()
            check(f"вкладка «{label}»", app.nb.get() == label
                  and app._current_tab == label
                  and app._tab_pill.cget("text") == label,
                  f"{app.nb.get()} / {app._current_tab}")

        print("[4] горячие клавиши")
        app._goto_tab("Имена персонажей")
        app.update()
        app.focus_force()
        app.nb.focus_set()
        app.update()
        third = list(app._tabs)[2]
        for _ in range(3):
            app.event_generate("<Control-Key-3>")
            app.update()
            time.sleep(0.05)
            if app._current_tab == third:
                break
        check(f"Ctrl+3 → «{third}»", app._current_tab == third,
              app._current_tab)
        for _ in range(3):
            app.event_generate("<Control-Key-6>")
            app.update()
            time.sleep(0.05)
            if app._current_tab == gui_ctk.LOG_TAB:
                break
        check("Ctrl+6 → журнал", app._current_tab == gui_ctk.LOG_TAB,
              app._current_tab)

        # 24.10: быстрая смена вкладок не должна оставлять пустое окно
        app._goto_tab("Замены")
        app._goto_tab(gui_ctk.LOG_TAB)
        for _ in range(8):
            app.update()
            time.sleep(0.05)
        check("быстрая смена вкладок: журнал виден",
              app._log_panel.winfo_ismapped() == 1,
              f"mapped={app._log_panel.winfo_ismapped()}")

        app.runner.status_fn("выполняется: тест")
        app.update()
        check("статус обновляется", "тест" in app.status.cget("text"),
              app.status.cget("text"))
        app.status.configure(text="готов")

        print("[5] история путей")
        vault_tab = app._tabs["Хранилище"]
        field = vault_tab.f_vault
        for i in range(12):
            field._remember(f"C:/tmp/path_{i}")
        hist = field._history_list()
        check("история ограничена 10", len(hist) == 10, str(len(hist)))
        check("свежий путь сверху", hist[0] == "C:/tmp/path_11", hist[0])
        field._remember("C:/tmp/path_5")
        hist = field._history_list()
        check("дубль поднят наверх", hist[0] == "C:/tmp/path_5"
              and hist.count("C:/tmp/path_5") == 1, str(hist[:3]))
        stored = gui_config.CFG.get("gui.path_history")
        check("история в gui.path_history",
              isinstance(stored, dict) and stored.get("vault_input"),
              str(type(stored)))
        check("старые 5 путей не потерялись",
              isinstance(gui_config.CFG.get("names_input_recent"), list))

        print("[6] журнал")
        log = app._log_panel
        app._goto_tab(gui_ctk.LOG_TAB)
        app.update()
        log.clear()
        log.append("строка раз\n")
        log.append("строка два\n", "ok")
        check("запись в журнал", "строка два" in log.get_text())
        log.search_var.set("строка")
        log.run_search()
        app.update()
        check("поиск с подсветкой", "найдено: 2"
              in log.search_label.cget("text"),
              log.search_label.cget("text"))
        check("тег найденного существует",
              bool(log.text.tag_ranges("found")))
        log.clear_search()
        check("сброс поиска", not log.text.tag_ranges("found")
              and log.search_var.get() == "")
        old = log._font_size
        log.zoom(1)
        check("масштаб журнала", log._font_size == old + 1
              and gui_config.CFG.get("ui.log_font") == old + 1)
        log.zoom(-1)
        log.copy_all()
        check("копирование журнала", "строка" in app.clipboard_get())

        # 24.10: умный автоскролл — вверх не утаскивает, возврат вниз следит
        log.clear()
        for i in range(120):
            log.append(f"строка {i}\n")
        app.update()
        log._sync_follow()
        check("слежение у низа", log._follow is True,
              f"follow={log._follow}")

        log.text.yview_moveto(0)
        app.update()
        log._sync_follow()
        top = log.text.yview()[0]
        log.append("новая строка при прокрутке вверх\n")
        app.update()
        check("прокрутка вверх останавливает слежение",
              log._follow is False and abs(log.text.yview()[0] - top) < 0.01,
              f"follow={log._follow} top={log.text.yview()[0]}")

        log.text.yview_moveto(1.0)
        app.update()
        log._sync_follow()
        log.append("снова внизу\n")
        app.update()
        check("возврат вниз включает слежение",
              log._follow is True and log.text.yview()[1] > 0.99,
              f"follow={log._follow} bottom={log.text.yview()[1]}")

        log.clear()
        check("очистка журнала", log.get_text() == "")

        # 24.10: лимит строк применяется без перезапуска
        gui_config.CFG.set("ui.log_limit", 600)
        for i in range(1000):
            log.append(f"строка {i}\n")
        total = int(log.text.index("end-1c").split(".")[0])
        check("лимит строк журнала", total <= 900, f"строк {total}")
        gui_config.CFG.set("ui.log_limit", 5000)
        log.clear()

        print("[7] тема и тосты")
        app._on_theme_change("light")
        app.update()
        check("светлая тема", ctk.get_appearance_mode().lower() == "light")
        app._on_theme_change("dark")
        app.update()
        check("тёмная тема", ctk.get_appearance_mode().lower() == "dark")
        app.toast("проверка", "info", beep=False)
        app.update()
        check("тост показан", len(gui_ctk.App._toast_stack) > 0)
        for win in list(gui_ctk.App._toast_stack):
            try:
                win.destroy()
            except Exception:
                pass
        gui_ctk.App._toast_stack.clear()

        print("[8] настройки окна и журнала")
        settings = app._tabs["Настройки"]
        check("в настройках есть папка отчётов",
              hasattr(settings, "f_report_dir"))
        check("в настройках есть лимит журнала",
              hasattr(settings, "f_log_limit"))
        # 24.10: плейсхолдер должен быть виден и без textvariable
        settings.f_log_limit.set("")
        app.focus_set()
        app.update()
        try:
            settings.f_log_limit.entry._entry_focus_out()
        except Exception:
            pass
        app.update()
        check("плейсхолдер поля виден",
              settings.f_log_limit.entry._placeholder_text_active is True)
        settings.f_log_limit.entry.insert(0, "8888")
        settings.f_log_limit._on_edit()
        check("ввод без KeyRelease попадает в конфиг",
              str(gui_config.CFG.get("ui.log_limit")) == "8888",
              str(gui_config.CFG.get("ui.log_limit")))
        settings.f_log_limit.set("7000")
        check("лимит журнала сохранён",
              str(gui_config.CFG.get("ui.log_limit")) == "7000",
              str(gui_config.CFG.get("ui.log_limit")))

        # 25.10: «Выкл» — отдельный флаг script_preset, а не очистка полей.
        saved_preset = gui_config.CFG.get("script_preset", "auto")
        saved_fields = {key: field.get()
                        for key, field in settings._script_fields.items()}
        test_paths = {key: f"C:/tmp/{key}.py"
                      for key in settings._script_fields}
        for key, field in settings._script_fields.items():
            field.set(test_paths[key])
        settings._on_preset("Выкл")
        check("«Выкл» не стирает ручные пути",
              all(field.get() == test_paths[key]
                  for key, field in settings._script_fields.items()),
              str({key: field.get()
                   for key, field in settings._script_fields.items()}))
        from wrappers import script_path
        check("«Выкл» отключает запуск внешних скриптов",
              all(script_path(key) == "" for key in settings._script_fields),
              str({key: script_path(key) for key in settings._script_fields}))
        settings._on_preset("Вручную")
        check("«Вручную» возвращает сохранённые пути",
              all(field.get() == test_paths[key]
                  for key, field in settings._script_fields.items()),
              str({key: field.get()
                   for key, field in settings._script_fields.items()}))
        settings._fill_auto(switch=False)
        from wrappers import script_preset
        check("«Найти скрипты» не меняет ручной пресет",
              script_preset() == "manual", script_preset())
        for key, field in settings._script_fields.items():
            field.set(saved_fields.get(key, ""))
        gui_config.CFG.set("script_preset", saved_preset)
        settings.preset.set({"auto": "Авто", "manual": "Вручную",
                             "off": "Выкл"}.get(saved_preset, "Авто"))
        settings._update_preset_hint()

        reports_dir = Path(tempfile.gettempdir()) / "textools_reports_check"
        settings.f_report_dir.set(str(reports_dir))
        resolved = app._reports_dir()
        check("папка отчётов применяется",
              resolved == reports_dir and resolved.is_dir(), str(resolved))

        vault_tab.f_vault.set("C:/tmp/set_test")
        check("PathField.set пишет значение",
              vault_tab.f_vault.get() == "C:/tmp/set_test",
              vault_tab.f_vault.get())

        def find_check(key):
            for w in buttons_and_all:
                if getattr(w, "key", None) == key:
                    return w
            return None

        def all_widgets(w):
            yield w
            for c in w.winfo_children():
                yield from all_widgets(c)

        buttons_and_all = list(all_widgets(app))
        cc = find_check("confirm_close")
        check("настройка подтверждения закрытия есть", cc is not None)
        if cc is not None:
            cc.var.set(False)
            cc._save()
            check("подтверждение закрытия выключается",
                  gui_config.CFG.get("confirm_close") is False)
            cc.var.set(True)
            cc._save()

        check("настройка размера окна есть",
              find_check("remember_geometry") is not None)
        check("настройка «не создавать .bak» есть",
              find_check("obs_no_bak") is not None)
        check("поле расширений для иероглифов есть",
              find_check("cjk_ext") is not None)
        settings.f_cjk_ext.set("MD, txt")
        settings._check_cjk_ext()
        check("расширения CJK нормализуются",
              settings.f_cjk_ext.get() == ".md,.txt",
              settings.f_cjk_ext.get())
        settings.f_log_limit.set("100")
        settings._check_log_limit()
        check("лимит журнала не ниже 500",
              settings.f_log_limit.get() == "5000",
              settings.f_log_limit.get())
        settings.f_log_limit.set("7000")
        rt = find_check("remember_tab")
        check("настройка последней вкладки есть", rt is not None)
        if rt is not None:
            app._goto_tab("Чистка")
            gui_config.CFG.set("ui.last_tab", "Имена персонажей")
            rt.var.set(False)
            rt._save()
            app._save_ui_state()
            check("без запоминания вкладка не пишется",
                  gui_config.CFG.get("ui.last_tab") == "Имена персонажей",
                  str(gui_config.CFG.get("ui.last_tab")))
            rt.var.set(True)
            rt._save()

        app.reset_geometry()
        check("размер окна сброшен",
              gui_config.CFG.get("ui.geometry") == ""
              and "x" in app.geometry(), str(app.geometry()))

        check("фоновая задача запускается",
              app.begin_background("тест-витрина") is True)
        app.update()
        check("фоновая задача блокирует кнопки",
              app._bg_active and str(app._stop_btn.cget("state")) == "normal")
        check("второй запуск при фоне отклоняется",
              app.begin_run() is False)
        app.stop_all()
        check("стоп ставит флаг", gui_ctk.STOP_FILE.exists())
        app.finish_background()
        app.update()
        check("фоновая задача завершается",
              not app._bg_active
              and str(app._stop_btn.cget("state")) == "disabled"
              and not gui_ctk.STOP_FILE.exists())

        # 24.10: восстановление эмодзи гасит dry-run и бэкап
        clean_tab = app._tabs["Чистка"]
        clean_tab.c_res.var.set(True)
        app.update()
        check("восстановление гасит dry-run",
              str(clean_tab.c_dry.cget("state")) == "disabled",
              str(clean_tab.c_dry.cget("state")))
        clean_tab.c_res.var.set(False)
        app.update()

        # 24.10: мягкая остановка не убивает процесс мгновенно
        class _DummyProc:
            killed = False

            def kill(self):
                self.killed = True

        dummy = gui_ctk.Runner(lambda *a: None, lambda *a: None, app)
        dummy.running = True
        dummy._run_id = 1
        dummy.proc = _DummyProc()
        dummy.stop()
        time.sleep(0.4)
        check("стоп ждёт, а не убивает сразу", not dummy.proc.killed)
        dummy.running = False
        time.sleep(0.2)
        try:
            gui_ctk.STOP_FILE.unlink(missing_ok=True)
        except Exception:
            pass

        # 24.10: витрина открывается модально и закрывается без следов
        import review_dialog
        win = review_dialog.show(
            app, [("фраза", "", "f.md", 1, "…фраза…")],
            lambda pairs: [("ok\n", "ok")])
        app.update()
        check("витрина открывается", win.winfo_exists() == 1)
        check("витрина модальная", win.grab_current() is not None)
        try:
            win.grab_release()
        except Exception:
            pass
        win.destroy()
        app.update()

        gui_config.CFG.set("sound", False)
        app._on_done(1, 1.0, stopped=True)
        check("остановка не считается ошибкой",
              app.status.cget("text") == "остановлено",
              app.status.cget("text"))
        for win in list(gui_ctk.App._toast_stack):
            try:
                win.destroy()
            except Exception:
                pass
        gui_ctk.App._toast_stack.clear()
        app.status.configure(text="готов")

        print("[9] новые инструменты")
        calls2 = []
        orig_int2 = gui_ctk.run_internal
        orig_cmd2 = gui_ctk.run_cmd
        try:
            gui_ctk.run_internal = lambda mod, args: calls2.append(
                ("internal", mod, tuple(args)))
            gui_ctk.run_cmd = lambda cmd: calls2.append(("cmd", tuple(cmd)))
            vault_tab.f_obs.set("C:/tmp/vault")
            vault_tab.c_obs_fix.var.set(True)
            gui_config.CFG.set("obs_no_bak", True)
            vault_tab._run_obsidian()
            vault_tab.f_cjk.set("C:/tmp/vault")
            vault_tab.c_cjk_json.var.set(False)
            gui_config.CFG.set("cjk_ext", ".md")
            vault_tab._run_cjk()
        finally:
            gui_ctk.run_internal = orig_int2
            gui_ctk.run_cmd = orig_cmd2
        obs = [c for c in calls2 if c[0] == "internal"]
        cjk = [c for c in calls2 if c[0] == "cmd"]
        check("obsidian-check запускается с --fix и --exit-zero",
              bool(obs) and obs[0][1] == "obsidian_check"
              and "--fix" in obs[0][2] and "--exit-zero" in obs[0][2],
              str(obs[:1]))
        check("настройка «не создавать .bak» доходит до obsidian-check",
              bool(obs) and "--no-bak" in obs[0][2], str(obs[:1]))
        check("find_cjk запускается отдельным процессом",
              bool(cjk) and any("find_cjk.py" in str(x) for x in cjk[0][1]),
              str(cjk[:1]))
        check("расширения из настроек доходят до find_cjk",
              bool(cjk) and "--ext" in cjk[0][1], str(cjk[:1]))
        check("find_cjk запускается без --exit-zero",
              bool(cjk) and "--exit-zero" not in cjk[0][1], str(cjk[:1]))
        orig_beep = gui_ctk._toast_beep
        orig_flag = gui_ctk._cfg_flag
        try:
            gui_ctk._toast_beep = lambda level: None
            gui_ctk._cfg_flag = lambda *args, **kwargs: False
            app.runner._label = "find_cjk"
            app._on_done(1, 0.1)
            check("find_cjk: код 1 — «есть замечания»",
                  app.status.cget("text") == "есть замечания",
                  app.status.cget("text"))
        finally:
            gui_ctk._toast_beep = orig_beep
            gui_ctk._cfg_flag = orig_flag
            app.status.configure(text="готов")

        print("[10] состояние окна")
        app._save_ui_state()
        check("геометрия сохранена",
              str(gui_config.CFG.get("ui.geometry", "")).count("x") == 1,
              str(gui_config.CFG.get("ui.geometry")))
        check("вкладка сохранена",
              gui_config.CFG.get("ui.last_tab") in app._tabs,
              str(gui_config.CFG.get("ui.last_tab")))
    except Exception:
        failures.append("исключение")
        traceback.print_exc()
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
        if _config_bytes is not None:
            CONFIG.write_bytes(_config_bytes)
        gui_config.reset()

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
