# -*- coding: utf-8 -*-
"""Диалог-витрина чистки штампов и ё/е-аудита (01.10, 24.10).

Список вхождений с контекстом, галочки, выборочное применение.
Применение идёт в фоновом потоке, но сообщения возвращаются в главный
поток через очередь: Tk нельзя трогать из чужого потока.
"""
import queue
import threading

import customtkinter as ctk

from widgets_ctk import ActionButton, FONT_BOLD, FONT_PILL, FONT_TINY

MAX_ROWS = 400


def show(owner, hits, on_apply):
    """hits: [(phrase, repl, file, line_no, fragment)];
    on_apply(pairs) выполняется в фоновом потоке и возвращает список
    (текст, тег) или просто строк; pairs=[(phrase, файл, строка)] —
    04.11: номер строки доходит до инструментов, правятся только
    отмеченные вхождения."""
    win = ctk.CTkToplevel(owner)
    win.title("Выберите вхождения")
    # 05.11: геометрия адаптируется к экрану. Было жёстко 980x640 —
    # на экране ниже 640px кнопки «Применить»/«Отмена» уходили за
    # нижний край, и применить выбор было невозможно.
    _sw = win.winfo_screenwidth()
    _sh = win.winfo_screenheight()
    win.geometry(f"{min(980, _sw - 40)}x{min(640, _sh - 120)}")
    win.transient(owner)
    win.attributes("-topmost", True)

    def _un_top():
        try:
            win.attributes("-topmost", False)
        except Exception:
            pass

    win.after(200, _un_top)

    def close():
        try:
            win.grab_release()
        except Exception:
            pass
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", close)
    win.bind("<Escape>", lambda e: close())
    try:
        win.wait_visibility()
        win.grab_set()
    except Exception:
        pass

    # 07.11 (редизайн): шапка диалога — заголовок + живой счётчик выбранных
    head = ctk.CTkFrame(win, fg_color="transparent")
    head.pack(fill="x", padx=14, pady=(12, 4))
    ctk.CTkLabel(head, text="Выберите вхождения",
                 font=FONT_BOLD, anchor="w").pack(side="left")
    total_rows = min(len(hits), MAX_ROWS)
    counter = ctk.CTkLabel(head, text="", font=FONT_PILL, anchor="e",
                           fg_color=("#f0edfc", "#262238"),
                           text_color=("#6d28d9", "#c4b5fd"),
                           corner_radius=8)
    counter.pack(side="right", padx=(10, 0))

    sub = f"Найдено вхождений: {len(hits)}"
    if len(hits) > MAX_ROWS:
        sub += f" (показаны первые {MAX_ROWS})"
    ctk.CTkLabel(win, text=sub, font=FONT_TINY, anchor="w",
                 text_color=("gray40", "gray55")
                 ).pack(fill="x", padx=14, pady=(0, 2))

    scroll = ctk.CTkScrollableFrame(win, fg_color="transparent",
                                    scrollbar_button_color=("#d3d6de", "#3a4052"),
                                    scrollbar_button_hover_color=("#8b5cf6", "#8b5cf6"))
    scroll.pack(fill="both", expand=True, padx=14)

    groups = {}  # phrase -> {"rows": [(var, file)], "master": var}
    all_vars = []

    def _update_counter(*_):
        try:
            n = sum(1 for v in all_vars if v.get())
            counter.configure(text=f"выбрано {n} из {total_rows}")
        except Exception:
            pass

    for ph, repl, f, ln, frag in hits[:MAX_ROWS]:
        if ph not in groups:
            action = f"→ «{repl}»" if repl else "→ удалить"
            frame = ctk.CTkFrame(scroll, fg_color=("#ffffff", "#1a1d24"),
                                 border_width=1,
                                 border_color=("#e3e6ec", "#2a2f3a"),
                                 corner_radius=8)
            frame.pack(fill="x", pady=(8, 2))
            ctk.CTkLabel(frame, text=f"«{ph}» {action}",
                         font=FONT_PILL, anchor="w"
                         ).pack(fill="x", padx=10, pady=(4, 0))
            master = ctk.BooleanVar(value=True)
            groups[ph] = {"rows": [], "frame": frame, "master": master}
        var = ctk.BooleanVar(value=True)
        all_vars.append(var)
        try:
            var.trace_add("write", _update_counter)
        except Exception:
            pass
        # 01.10: CTkCheckBox (customtkinter 6) не поддерживает wraplength —
        # длинные фрагменты обрезаем текстом
        row_text = f"{f} :{ln} — …{frag}…"
        if len(row_text) > 120:
            row_text = row_text[:117] + "…"
        cb = ctk.CTkCheckBox(groups[ph]["frame"],
                             text=row_text,
                             variable=var, font=FONT_TINY,
                             checkbox_width=18, checkbox_height=18)
        cb.pack(fill="x", padx=22, pady=1)
        groups[ph]["rows"].append((var, f, ln))

    def toggle_group(ph, val):
        for var, _f, _ln in groups[ph]["rows"]:
            var.set(val)

    for ph, g in groups.items():
        m = ctk.CTkCheckBox(g["frame"], text="все", variable=g["master"],
                            # 20.10: g тоже замыкаем как default — иначе
                            # «все» любой группы переключает строки последней
                            command=lambda ph=ph, g=g: toggle_group(
                                ph, g["master"].get()),
                            font=FONT_TINY)
        m.pack(anchor="w", padx=10, pady=(0, 4))
        all_vars.append(g["master"])
        try:
            g["master"].trace_add("write", _update_counter)
        except Exception:
            pass
    _update_counter()

    def apply_selected():
        pairs = [(ph, f, ln) for ph, g in groups.items()
                 for var, f, ln in g["rows"] if var.get()]
        if not pairs:
            # 24.10: пустой выбор не закрывает окно молча
            try:
                win.bell()
            except Exception:
                pass
            return
        # 04.11: запуск проверяется ДО закрытия окна — раньше окно с
        # галочками уничтожалось, и если операция уже шла, выбор
        # пропадал безвозвратно
        begin = getattr(owner, "begin_background", None)
        started = True
        if callable(begin):
            try:
                started = bool(begin("Применение витрины"))
            except Exception:
                started = False
            if not started:
                # другой запуск уже идёт — окно остаётся с выбором
                return
        close()
        results = queue.Queue()

        def worker():
            try:
                results.put(("ok", on_apply(pairs)))
            except Exception as e:
                results.put(("err", str(e)))

        threading.Thread(target=worker, daemon=True).start()

        def poll():
            try:
                kind, payload = results.get_nowait()
            except queue.Empty:
                try:
                    owner.after(120, poll)
                except Exception:
                    pass
                return
            try:
                if kind == "err":
                    owner.log_line(f"Ошибка применения: {payload}\n", "err")
                else:
                    for item in payload or []:
                        if isinstance(item, (tuple, list)):
                            text = item[0] if item else ""
                            tag = item[1] if len(item) > 1 else None
                        else:
                            text, tag = str(item), None
                        owner.log_line(text, tag)
            finally:
                if started:
                    try:
                        owner.finish_background()
                    except Exception:
                        pass

        owner.after(120, poll)

    btns = ctk.CTkFrame(win, fg_color="transparent")
    btns.pack(fill="x", padx=14, pady=10)
    ActionButton(btns, "Применить выбранные", apply_selected,
                 kind="danger", width=220).pack(side="left")
    ActionButton(btns, "Отмена", close,
                 kind="neutral", width=100).pack(side="left", padx=8)
    return win
