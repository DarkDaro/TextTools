"""Темы оформления: светлая и тёмная. Переключение на лету."""
import tkinter as tk
from tkinter import ttk

THEMES = {
    "light": {
        "bg": "#f4f5f7",          # фон окна
        "bg_card": "#ffffff",     # фон секций
        "bg_input": "#ffffff",    # фон полей ввода
        "bg_log": "#fbfbf8",      # фон лога
        "fg": "#1e2430",          # основной текст
        "fg_dim": "#6b7280",      # приглушённый текст
        "accent": "#7c3aed",      # акцент (фиолетовый, как в Obsidian)
        "accent_hover": "#6d28d9",
        "accent_text": "#ffffff",
        "success": "#059669",
        "warning": "#b45309",
        "danger": "#dc2626",
        "border": "#d1d5db",
        "help_bg": "#f5f2fd",     # фон блока-пояснения
        "help_border": "#ddd2f9",
        "tip_bg": "#1f2937",      # tooltip: тёмный даже в светлой теме
        "tip_fg": "#f9fafb",
        "tip_border": "#374151",
        "log_fg": "#111827",
        "sel": "#c4b5fd",
        "tab_active_bg": "#ffffff",
        "badge": "#ede9fe",
    },
    "dark": {
        "bg": "#111318",
        "bg_card": "#1a1d24",
        "bg_input": "#23262e",
        "bg_log": "#0d0f13",
        "fg": "#e5e7eb",
        "fg_dim": "#9ca3af",
        "accent": "#8b5cf6",      # 22.09: акцент в dark — средний фиолетовый,
                                  # белый текст читается; hover темнее для контраста
        "accent_hover": "#7c3aed",
        "accent_text": "#ffffff",
        "success": "#34d399",
        "warning": "#fbbf24",
        "danger": "#f87171",
        "border": "#374151",
        "help_bg": "#221f33",     # фон блока-пояснения
        "help_border": "#3b3357",
        "tip_bg": "#e5e7eb",      # tooltip: светлый в тёмной теме
        "tip_fg": "#111318",
        "tip_border": "#9ca3af",
        "log_fg": "#d1d5db",
        "sel": "#3b2d5c",
        "tab_active_bg": "#23262e",
        "badge": "#2e1f4f",
    },
}


class Theme:
    """Текущая тема + применение к виджетам."""

    _colors = dict(THEMES["light"])
    _listeners = []  # функции перерисовки (tooltip и т.п.)

    @classmethod
    def colors(cls):
        return cls._colors

    @classmethod
    def c(cls, name):
        return cls._colors[name]

    @classmethod
    def set_theme(cls, root, name):
        cls._colors = dict(THEMES[name])
        c = cls._colors
        style = ttk.Style(root)
        try:
            style.theme_use("clam")  # единственная тема, полностью красится
        except tk.TclError:
            pass

        # --- базовые стили ttk ---
        style.configure(".",
                        background=c["bg"], foreground=c["fg"],
                        fieldbackground=c["bg_input"],
                        bordercolor=c["border"],
                        lightcolor=c["bg_card"], darkcolor=c["bg_card"],
                        troughcolor=c["bg_log"],
                        font=("Segoe UI", 10))
        style.configure("TFrame", background=c["bg"])
        style.configure("TLabel", background=c["bg"], foreground=c["fg"])
        style.configure("Card.TFrame", background=c["bg_card"])
        style.configure("Card.TLabelframe", background=c["bg_card"],
                        bordercolor=c["border"], relief="solid",
                        borderwidth=1, padding=6)
        style.configure("Card.TLabelframe.Label", background=c["bg_card"],
                        foreground=c["accent"],
                        font=("Segoe UI", 10, "bold"))
        style.configure("TLabelframe", background=c["bg"],
                        bordercolor=c["border"])
        style.configure("TLabelframe.Label", background=c["bg"],
                        foreground=c["accent"], font=("Segoe UI", 10, "bold"))

        # --- поля ввода ---
        style.configure("TEntry", fieldbackground=c["bg_input"],
                        foreground=c["fg"], bordercolor=c["border"],
                        insertcolor=c["fg"], padding=4)
        style.map("TEntry",
                  bordercolor=[("focus", c["accent"])],
                  lightcolor=[("focus", c["accent"])])

        # --- кнопки: обычные и акцентные ---
        style.configure("TButton", background=c["bg_card"],
                        foreground=c["fg"], bordercolor=c["border"],
                        focuscolor=c["accent"], padding=(12, 7),
                        font=("Segoe UI", 10))
        style.map("TButton",
                  background=[("active", c["accent"]), ("pressed", c["accent_hover"])],
                  foreground=[("active", c["accent_text"])],
                  bordercolor=[("active", c["accent"])])

        style.configure("Accent.TButton", background=c["accent"],
                        foreground=c["accent_text"], borderwidth=0,
                        padding=(16, 9), font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton",
                  background=[("active", c["accent_hover"]),
                              ("pressed", c["accent_hover"])])

        style.configure("Danger.TButton", background=c["danger"],
                        foreground="#ffffff", borderwidth=0,
                        padding=(12, 7), font=("Segoe UI", 10, "bold"))
        style.map("Danger.TButton",
                  background=[("active", "#b91c1c")])

        # компактные кнопки (ряд под логом)
        style.configure("Compact.TButton", padding=(4, 2),
                        font=("Segoe UI", 9))

        # --- чекбоксы ---
        style.configure("TCheckbutton", background=c["bg_card"],
                        foreground=c["fg"], focuscolor=c["accent"],
                        padding=4, font=("Segoe UI", 10))
        style.map("TCheckbutton",
                  background=[("active", c["bg_card"])],
                  indicatorcolor=[("selected", c["accent"]),
                                  ("!selected", c["border"])])
        # чекбокс на общем фоне (вне секций)
        style.configure("Plain.TCheckbutton", background=c["bg"])
        style.map("Plain.TCheckbutton", background=[("active", c["bg"])])

        # --- вкладки ---
        style.configure("TNotebook", background=c["bg"], borderwidth=0,
                        tabmargins=[8, 6, 8, 0])
        style.configure("TNotebook.Tab", background=c["bg_card"],
                        foreground=c["fg_dim"], padding=(16, 9),
                        font=("Segoe UI", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", c["tab_active_bg"])],
                  foreground=[("selected", c["accent"])],
                  expand=[("selected", [1, 1, 1, 0])])

        # --- скроллбары ---
        style.configure("TScrollbar", background=c["bg_card"],
                        troughcolor=c["bg"], bordercolor=c["bg"],
                        arrowsize=13)
        style.map("TScrollbar",
                  background=[("active", c["accent"])])

        # --- спинбокс ---
        style.configure("TSpinbox", fieldbackground=c["bg_input"],
                        foreground=c["fg"], bordercolor=c["border"],
                        arrowcolor=c["fg"], padding=4)

        # --- root и лог ---
        root.configure(bg=c["bg"])

        for fn in cls._listeners:
            fn()

    @classmethod
    def on_theme_change(cls, fn):
        cls._listeners.append(fn)


def apply_log_theme(log_widget, theme_name):
    """Цвета текстового лога (tk.Text — не ttk, красится напрямую)."""
    c = THEMES[theme_name]
    log_widget.configure(
        bg=c["bg_log"], fg=c["log_fg"], insertbackground=c["fg"],
        selectbackground=c["sel"], selectforeground=c["fg"],
        font=("Consolas", 10))
    # теги подсветки
    log_widget.tag_configure("ok", foreground=c["success"])
    log_widget.tag_configure("warn", foreground=c["warning"])
    log_widget.tag_configure("err", foreground=c["danger"])
    log_widget.tag_configure("cmd", foreground=c["accent"],
                             font=("Consolas", 10, "bold"))
    log_widget.tag_configure("dim", foreground=c["fg_dim"])