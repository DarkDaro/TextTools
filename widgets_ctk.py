"""Обёртки CustomTkinter для textools. 18.09: полная переделка UI.
Все виджеты сохраняют прежний API (get/set/pack), чтобы вкладки
менялись минимально."""
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

import customtkinter as ctk

# 22.09: gui_theme.py остался только старому GUI (архив) — мёртвый импорт убран

# масштаб и вид по умолчанию
ctk.set_widget_scaling(1.0)
FONT = ("Segoe UI", 12)
FONT_SMALL = ("Segoe UI", 11)
FONT_MONO = ("Consolas", 11)


class Tooltip:
    """Всплывающая подсказка при наведении."""

    def __init__(self, widget, text, wraplength=380):
        self.widget = widget
        self.text = text
        self.wraplength = wraplength
        self.tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _e=None):
        if self.tip:
            return
        mode = ctk.get_appearance_mode()
        bg = "#2b2438"  # 22.09: тёмно-фиолетовый tooltip в обеих темах
        fg = "#f5f5f5"
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, justify="left", bg=bg, fg=fg,
                 wraplength=self.wraplength, padx=10, pady=6,
                 font=("Segoe UI", 10)).pack()
        self.tip.wm_deiconify()

    def _hide(self, _e=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class PathField(ctk.CTkFrame):
    """Поле пути: метка + entry + кнопки выбора. Автосохранение в конфиг."""

    def __init__(self, master, label, key, cfg, file_mode="both",
                 tooltip=None, width_label=160):
        super().__init__(master, fg_color="transparent")
        self.key = key
        self.cfg = cfg
        self.var = tk.StringVar(value=cfg.get(key))
        self.var.trace_add("write", self._autosave)
        self._label = label
        self._wl = width_label
        self._mode = file_mode
        self._tt = tooltip
        # 22.09: pack сам — как EntryField (иначе нулевая высота, поле невидимо)
        self.pack(fill="x", pady=3)
        self._build()

    def _autosave(self, *_):
        self.cfg.set(self.key, self.var.get())

    def _build(self):
        if self._label:
            lbl = ctk.CTkLabel(self, text=self._label, width=self._wl,
                               anchor="w", font=FONT)
            lbl.pack(side="left")
            if self._tt:
                Tooltip(lbl, self._tt)
        self.entry = ctk.CTkEntry(self, textvariable=self.var,
                                  font=FONT_MONO, height=30)
        self.entry.pack(side="left", fill="x", expand=True, padx=6)

        def browse_dir():
            cur = self.var.get()
            start = cur if Path(cur).is_dir() else str(Path(cur).parent) if cur else str(self.cfg.home)
            p = filedialog.askdirectory(initialdir=start)
            if p:
                self._set(p)

        def browse_file():
            cur = self.var.get()
            start = str(Path(cur).parent) if cur else str(self.cfg.home)
            p = filedialog.askopenfilename(
                initialdir=start,
                filetypes=[("Текст и документы", "*.md *.txt *.yaml *.yml *.docx *.log"),
                           ("Все файлы", "*.*")])
            if p:
                self._set(p)

        if self._mode in ("both", "dir"):
            ctk.CTkButton(self, text="Папка", width=70, height=30,
                          command=browse_dir).pack(side="left", padx=2)
        if self._mode in ("both", "file"):
            ctk.CTkButton(self, text="Файл", width=60, height=30,
                          command=browse_file).pack(side="left", padx=2)

    def _set(self, p):
        self.var.set(p)
        self.cfg.set(self.key, p)

    def get(self):
        return self.var.get().strip()


class EntryField(ctk.CTkFrame):
    """Поле ввода текста с меткой и плейсхолдером. Автосохранение."""

    def __init__(self, master, label, key, cfg, tooltip=None,
                 width_label=160, placeholder=""):
        super().__init__(master, fg_color="transparent")
        self.key = key
        self.cfg = cfg
        self.pack(fill="x", pady=3)
        self._placeholder = placeholder
        self.var = tk.StringVar(value=cfg.get(key))
        # 01.10: плейсхолдер рисует сам CTkEntry (placeholder_text) — раньше
        # значение писали в var, из-за чего ввод, совпавший с плейсхолдером,
        # считался пустотой и не сохранялся в конфиг
        self.var.trace_add("write", self._autosave)
        if label:
            lbl = ctk.CTkLabel(self, text=label, width=width_label,
                               anchor="w", font=FONT)
            lbl.pack(side="left")
            if tooltip:
                Tooltip(lbl, tooltip)
        elif tooltip:
            self._tt_after = tooltip  # подешевле: tooltip вешается снаружи
        self.entry = ctk.CTkEntry(self, textvariable=self.var,
                                  font=FONT_MONO, height=30,
                                  placeholder_text=placeholder or None)
        self.entry.pack(side="left", fill="x", expand=True, padx=4)
        if tooltip and not label:
            Tooltip(self.entry, tooltip)

    def _autosave(self, *_):
        self.cfg.set(self.key, self.var.get())

    def get(self):
        # 01.10: проверка на плейсхолдер убрана — нативный placeholder_text
        # не попадает в entry.get(), а реальный ввод совпадать с ним может
        return self.entry.get().strip()

    def set(self, v):
        self.var.set(v)
        self.cfg.set(self.key, v)


class CheckField(ctk.CTkCheckBox):
    """Чекбокс с сохранением состояния."""

    def __init__(self, master, label, key, cfg, default=False, tooltip=None):
        self.key = key
        self.cfg = cfg
        self.var = tk.BooleanVar(value=bool(cfg.get(key, default)))
        super().__init__(master, text=label, variable=self.var,
                         command=self._save, font=FONT,
                         checkbox_width=20, checkbox_height=20)
        if tooltip:
            Tooltip(self, tooltip)

    def _save(self):
        self.cfg.set(self.key, self.var.get())

    def get(self):
        return self.var.get()

    def pack(self, **kw):
        # CTkCheckBox pack: добавляю отступы по умолчанию
        kw.setdefault("pady", 4)
        return super().pack(**kw)


class HelpBox(ctk.CTkFrame):
    """Блок-пояснение «как это работает». Перенос текста подстраивается
    под фактическую ширину блока (раньше wraplength был фиксированным)."""

    def __init__(self, master, text):
        super().__init__(master, fg_color=("gray88", "gray17"),
                         corner_radius=8)
        self.pack(fill="x", pady=(0, 10))
        lbl = ctk.CTkLabel(self, text="Как это работает",
                           font=("Segoe UI", 12, "bold"), anchor="w")
        lbl.pack(fill="x", padx=12, pady=(8, 0))
        self._body = ctk.CTkLabel(self, text=text, justify="left", anchor="w",
                                  font=FONT_SMALL, wraplength=900)
        self._body.pack(fill="x", padx=12, pady=(2, 10))
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        # padx=12 с обеих сторон; на узком окне текст больше не обрезается
        wl = max(200, event.width - 24)
        if self._body.cget("wraplength") != wl:
            self._body.configure(wraplength=wl)


class Section(ctk.CTkFrame):
    """Секция-карточка с заголовком. Использование:
    s = Section(parent, 'Заголовок'); виджеты пакуют в s.inner.
    (совместимость: вкладки правятся на s.inner)"""

    def __init__(self, master, title, padding=14):
        super().__init__(master, fg_color=("gray92", "gray14"),
                         corner_radius=8)
        self.pack(fill="x", pady=(0, 12))
        self._pad = padding
        ctk.CTkLabel(self, text=title, font=("Segoe UI", 12, "bold"),
                     anchor="w").pack(fill="x", padx=padding, pady=(10, 4))
        self.inner = ctk.CTkFrame(self, fg_color="transparent")
        self.inner.pack(fill="x", padx=padding, pady=(0, padding))


class BigButton(ctk.CTkButton):
    """Крупная акцентная кнопка — основное действие."""

    def __init__(self, master, text, command, tooltip=None):
        # 22.09: фиолетовый акцент по текущей теме
        dark = ctk.get_appearance_mode().lower() == "dark"
        accent = "#8b5cf6" if dark else "#7c3aed"
        hover = "#7c3aed" if dark else "#6d28d9"
        super().__init__(master, text=text, command=command,
                         height=34, font=("Segoe UI", 12, "bold"),
                         fg_color=accent, hover_color=hover,
                         text_color="#ffffff",
                         cursor="hand2")
        self.pack(anchor="w", pady=(8, 0))
        if tooltip:
            Tooltip(self, tooltip)