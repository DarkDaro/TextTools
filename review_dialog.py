# -*- coding: utf-8 -*-
"""Диалог-витрина чистки штампов (01.10): список вхождений с контекстом,
галочки, выборочное применение. Запускается из вкладки «Хранилище»."""
import threading

import customtkinter as ctk

MAX_ROWS = 400


def show(owner, hits, on_apply):
    """hits: [(phrase, repl, file, line_no, fragment)];
    on_apply(pairs) вызывается в фоновом потоке: pairs=[(phrase, file)]."""
    win = ctk.CTkToplevel(owner)
    win.title("Чистка штампов — выберите вхождения")
    win.geometry("980x640")
    win.attributes("-topmost", True)
    win.after(200, lambda: win.attributes("-topmost", False))

    ctk.CTkLabel(win, text=f"Найдено вхождений: {len(hits)}"
                           + (f" (показаны первые {MAX_ROWS})"
                              if len(hits) > MAX_ROWS else ""),
                 font=("Segoe UI", 12, "bold"), anchor="w"
                 ).pack(fill="x", padx=14, pady=(12, 4))

    scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
    scroll.pack(fill="both", expand=True, padx=14)

    groups = {}  # phrase -> {"rows": [(var, file)], "master": var}
    for ph, repl, f, ln, frag in hits[:MAX_ROWS]:
        if ph not in groups:
            action = f"→ «{repl}»" if repl else "→ удалить"
            frame = ctk.CTkFrame(scroll, fg_color=("gray92", "gray14"),
                                 corner_radius=6)
            frame.pack(fill="x", pady=(8, 2))
            ctk.CTkLabel(frame, text=f"«{ph}» {action}",
                         font=("Segoe UI", 11, "bold"), anchor="w"
                         ).pack(fill="x", padx=10, pady=(4, 0))
            master = ctk.BooleanVar(value=True)
            groups[ph] = {"rows": [], "frame": frame, "master": master,
                          "mvar": None}

        var = ctk.BooleanVar(value=True)
        # 01.10: CTkCheckBox (customtkinter 6) не поддерживает wraplength —
        # длинные фрагменты обрезаем текстом
        row_text = f"{f} :{ln} — …{frag}…"
        if len(row_text) > 120:
            row_text = row_text[:117] + "…"
        cb = ctk.CTkCheckBox(groups[ph]["frame"],
                             text=row_text,
                             variable=var, font=("Segoe UI", 10),
                             checkbox_width=18, checkbox_height=18)
        cb.pack(fill="x", padx=22, pady=1)
        groups[ph]["rows"].append((var, f))

    def toggle_group(ph, val):
        for var, _f in groups[ph]["rows"]:
            var.set(val)

    for ph, g in groups.items():
        m = ctk.CTkCheckBox(g["frame"], text="все", variable=g["master"],
                            command=lambda ph=ph: toggle_group(
                                ph, g["master"].get()),
                            font=("Segoe UI", 10))
        m.pack(anchor="w", padx=10, pady=(0, 4))

    def apply_selected():
        pairs = [(ph, f) for ph, g in groups.items()
                 for var, f in g["rows"] if var.get()]
        win.destroy()
        threading.Thread(target=on_apply, args=(pairs,), daemon=True).start()

    btns = ctk.CTkFrame(win, fg_color="transparent")
    btns.pack(fill="x", padx=14, pady=10)
    ctk.CTkButton(btns, text="Очистить выбранные", height=34,
                  fg_color="#8b5cf6", hover_color="#7c3aed",
                  command=apply_selected).pack(side="left")
    ctk.CTkButton(btns, text="Отмена", height=34, width=90,
                  fg_color=("gray75", "gray30"),
                  command=win.destroy).pack(side="left", padx=8)
    return win
