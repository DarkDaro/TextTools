"""Обёртки CustomTkinter для textools. 18.09: полная переделка UI.

24.10: виджеты приведены к общему UI-стандарту (UI_DESIGN.md):
карточки с рамкой, семантические кнопки, история путей на 10 значений,
панель журнала с поиском, автопрокруткой и масштабом шрифта.
Все виджеты сохраняют прежний API (get/set/pack), чтобы вкладки
менялись минимально."""
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

import customtkinter as ctk

# 22.09: gui_theme.py остался только старому GUI (архив) — мёртвый импорт убран

# 02.10: drag&drop путей (tkinterdnd2 — опционально, без него всё работает)
try:
    from tkinterdnd2 import DND_FILES as _DND_FILES
    _DND_LIB = True
except Exception:
    _DND_LIB = False

DND_ENABLED = False


def enable_dnd(root_window):
    """Подключить tkdnd к существующему root (вызвать один раз до
    построения полей). False — если библиотеки нет (мягкая деградация)."""
    global DND_ENABLED
    if not _DND_LIB:
        return False
    try:
        from tkinterdnd2 import TkinterDnD
        TkinterDnD._require(root_window)
        DND_ENABLED = True
    except Exception:
        DND_ENABLED = False
    return DND_ENABLED


def _drop_first_path(event):
    """Первый путь из события: пути с пробелами приходят в {...}."""
    data = event.data.strip()
    if data.startswith("{"):
        return data[1:].split("}")[0]
    return data.split(" ")[0].strip("{}")


def _clean_clip_path(data):
    """21.10: путь из буфера подчищается: Explorer «Копировать как путь»
    обрамляет путь двойными кавычками, переводы строк заменяются пробелом."""
    data = (data or "").strip().strip('"').strip()
    return data.replace("\r\n", " ").replace("\n", " ").strip()


def attach_clip_menu(entry, extra=None, on_change=None):
    """21.10: правая кнопка мыши в поле — Копировать/Вставить/Очистить.
    Вставка подчищает кавычки и переводы строк («Копировать как путь»).
    extra — кортеж (подпись, команда): дополнительный пункт, например
    «Вставить и выбрать папку» для полей путей.
    24.10: on_change — уведомить поле, что текст изменён не клавиатурой
    (после удаления textvariable у EntryField)."""
    menu = tk.Menu(entry, tearoff=0, font=("Segoe UI", 10))

    def changed():
        if callable(on_change):
            try:
                on_change()
            except Exception:
                pass

    def paste():
        try:
            data = _clean_clip_path(entry.clipboard_get())
        except Exception:
            return
        if data:
            entry.insert(entry.index("insert"), data)
            changed()

    def copy_all():
        data = entry.get()
        if data:
            entry.clipboard_clear()
            entry.clipboard_append(data)

    menu.add_command(label="Вставить из буфера", command=paste)
    menu.add_command(label="Копировать всё", command=copy_all)
    if extra:
        menu.add_command(label=extra[0], command=extra[1])
    menu.add_separator()
    menu.add_command(label="Очистить поле",
                     command=lambda: (entry.delete(0, "end"), changed()))

    def popup(e):
        try:
            menu.tk_popup(e.x_root, e.y_root)
        finally:
            menu.grab_release()
        return "break"

    entry.bind("<Button-3>", popup)
    return menu


# 24.10: служебные кнопки (выбор пути, панель журнала) — не синие
# по умолчанию CTk, а нейтральные в обеих темах
SMALL_BUTTON = {
    "fg_color": ("#e9e7f4", "#262a34"),
    "hover_color": ("#dcd8ee", "#343a48"),
    "text_color": ("#3b3557", "#d5d2e6"),
}


# масштаб и вид по умолчанию
ctk.set_widget_scaling(1.0)
FONT = ("Segoe UI", 12)
FONT_SMALL = ("Segoe UI", 11)
FONT_MONO = ("Consolas", 11)

# 24.10: история путей общая для всех полей, привязана к смыслу ключом
HISTORY_KEY = "gui.path_history"
HISTORY_LIMIT = 10


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
        bg = "#2b2438"  # 22.09: тёмно-фиолетовый tooltip в обеих темах
        fg = "#f5f5f5"
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        tk.Label(self.tip, text=self.text, justify="left", bg=bg, fg=fg,
                 wraplength=self.wraplength, padx=10, pady=6,
                 font=("Segoe UI", 10)).pack()
        self.tip.update_idletasks()
        # 24.10: подсказка не уезжает за правый/нижний край экрана
        sw = self.widget.winfo_screenwidth()
        sh = self.widget.winfo_screenheight()
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        if x + self.tip.winfo_width() > sw - 8:
            x = max(8, sw - self.tip.winfo_width() - 8)
        if y + self.tip.winfo_height() > sh - 8:
            y = max(8, self.widget.winfo_rooty() - self.tip.winfo_height() - 4)
        self.tip.wm_geometry(f"+{x}+{y}")
        self.tip.wm_deiconify()

    def _hide(self, _e=None):
        if self.tip:
            try:
                self.tip.destroy()
            except Exception:
                pass
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
        # 24.10: старый ключ <key>_recent больше не пишется; он читается
        # только как запасной вариант в _history_list (миграция истории)
        self._label = label
        self._wl = width_label
        self._mode = file_mode
        self._tt = tooltip
        # 22.09: pack сам — как EntryField (иначе нулевая высота, поле невидимо)
        self.pack(fill="x", pady=3)
        self._build()

    def _autosave(self, *_):
        self.cfg.set(self.key, self.var.get().strip().strip('"').strip())

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
        # 24.10: путь, набранный руками, тоже попадает в историю
        self.entry.bind("<FocusOut>", self._remember_current)
        # 01.10: подсказка и на поле, не только на метке
        if self._tt:
            Tooltip(self.entry, self._tt)

        def browse_dir():
            cur = self.get()
            start = cur if Path(cur).is_dir() else str(Path(cur).parent) if cur else str(self.cfg.home)
            p = filedialog.askdirectory(initialdir=start)
            if p:
                self._set(p)

        def browse_file():
            cur = self.get()
            start = str(Path(cur).parent) if cur else str(self.cfg.home)
            p = filedialog.askopenfilename(
                initialdir=start,
                filetypes=[("Текст и документы", "*.md *.txt *.yaml *.yml *.docx *.log"),
                           ("Все файлы", "*.*")])
            if p:
                self._set(p)

        # 24.10: по стандарту одно поле + «…» + «▾» с историей.
        # Для режима both «…» выбирает папку, отдельная кнопка «Файл» —
        # один файл (частая операция, терять её нельзя).
        b_pick = ctk.CTkButton(self, text="…", width=34, height=30,
                               font=("Segoe UI", 14, "bold"),
                               command=browse_dir if self._mode in ("both", "dir")
                               else browse_file, **SMALL_BUTTON)
        b_pick.pack(side="left", padx=(0, 2))
        Tooltip(b_pick, "Выбрать папку. Обход рекурсивный, включая подпапки."
                if self._mode in ("both", "dir") else "Выбрать файл.")
        if self._mode == "both":
            b_file = ctk.CTkButton(self, text="Файл", width=54, height=30,
                                   command=browse_file, **SMALL_BUTTON)
            b_file.pack(side="left", padx=(0, 2))
            Tooltip(b_file, "Выбрать отдельный файл — обработается только он.")
        # 02.10: список недавних путей этого поля
        b_recent = ctk.CTkButton(self, text="▾", width=28, height=30,
                                 command=self._show_recent, **SMALL_BUTTON)
        b_recent.pack(side="left", padx=(0, 2))
        Tooltip(b_recent, "Недавние пути этого поля (последние 10).")
        self._recent_btn = b_recent
        # 02.10: drag&drop папки/файла прямо в поле
        if DND_ENABLED:
            try:
                for w in (self.entry, self):
                    w.drop_target_register(_DND_FILES)
                    w.bind("<<Drop>>", self._on_drop)
            except Exception:
                pass
        # 21.10: правый клик — Копировать/Вставить/Очистить; вставленный
        # путь чистится от кавычек («Копировать как путь» в Explorer).
        # 21.10+: «Вставить и выбрать папку/файл» — вставка из буфера
        # и сразу диалог выбора, стартующий с этого пути.
        def _paste_and_pick():
            try:
                data = _clean_clip_path(self.entry.clipboard_get())
            except Exception:
                return
            if not data:
                return
            home = str(getattr(self.cfg, "home", "."))
            self._set(data)
            if self._mode in ("both", "dir"):
                start = data if Path(data).is_dir() else \
                    (str(Path(data).parent) if Path(data).parent.exists()
                     else home)
                p = filedialog.askdirectory(initialdir=start)
            else:
                start = str(Path(data).parent) if \
                    Path(data).parent.exists() else home
                p = filedialog.askopenfilename(
                    initialdir=start,
                    filetypes=[("Текст и документы",
                                "*.md *.txt *.yaml *.yml *.docx *.log"),
                               ("Все файлы", "*.*")])
            if p:
                self._set(p)

        label = ("Вставить и выбрать папку…" if self._mode in ("both", "dir")
                 else "Вставить и выбрать файл…")
        self._clip_menu = attach_clip_menu(self.entry, extra=(label, _paste_and_pick))

    def _set(self, p):
        p = (p or "").strip().strip('"').strip()
        self.var.set(p)
        self.cfg.set(self.key, p)
        self._remember(p)

    def set(self, p):
        """24.10: публичный сеттер, как у EntryField (удобно и вкладкам,
        и автотестам)."""
        self._set(p)

    def _remember(self, p):
        """24.10: путь в общую историю поля (10 последних, без дублей,
        свежие сверху). Хранение — CFG gui.path_history по смыслу поля;
        старый ключ <key>_recent читается как запасной вариант."""
        try:
            hist = self.cfg.get(HISTORY_KEY)
            hist = dict(hist) if isinstance(hist, dict) else {}
            rec = self._history_list()
            if p in rec:
                rec.remove(p)
            rec.insert(0, p)
            hist[self.key] = rec[:HISTORY_LIMIT]
            self.cfg.set(HISTORY_KEY, hist)
        except Exception:
            pass

    def _remember_current(self, _e=None):
        p = self.get()
        if p:
            self._remember(p)

    def _history_list(self):
        hist = self.cfg.get(HISTORY_KEY)
        rec = hist.get(self.key) if isinstance(hist, dict) else None
        if not isinstance(rec, list):
            legacy = self.cfg.get(f"{self.key}_recent")
            rec = list(legacy) if isinstance(legacy, list) else []
        return [r for r in rec if isinstance(r, str) and r][:HISTORY_LIMIT]

    def _show_recent(self):
        menu = tk.Menu(self, tearoff=0, font=("Segoe UI", 10))
        rec = self._history_list()
        if not rec:
            menu.add_command(label="(нет недавних путей)", state="disabled")
        for r in rec:
            menu.add_command(label=(r if len(r) <= 70 else "…" + r[-69:]),
                             command=lambda rr=r: self._set(rr))
        x = self._recent_btn.winfo_rootx()
        y = self._recent_btn.winfo_rooty() + self._recent_btn.winfo_height() + 2
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _on_drop(self, event):
        p = _drop_first_path(event)
        if p:
            self._set(p)

    def get(self):
        # 24.10: путь из Проводника может прийти в кавычках
        return self.var.get().strip().strip('"').strip()


class EntryField(ctk.CTkFrame):
    """Поле ввода текста с меткой и плейсхолдером. Автосохранение.

    24.10: textvariable больше не передаётся в CTkEntry. Из-за него
    встроенный плейсхолдер не показывался (CTk проверяет textvariable
    на пустоту), и подсказки вроде «5000» или «необязательно» были
    невидимы. Теперь поле синхронизируется с var вручную.
    """

    def __init__(self, master, label, key, cfg, tooltip=None,
                 width_label=160, placeholder=""):
        super().__init__(master, fg_color="transparent")
        self.key = key
        self.cfg = cfg
        self.pack(fill="x", pady=3)
        self._placeholder = placeholder
        value = cfg.get(key)
        self.var = tk.StringVar(value="" if value is None else str(value))
        self.var.trace_add("write", self._autosave)
        self.var.trace_add("write", self._sync_entry)
        if label:
            lbl = ctk.CTkLabel(self, text=label, width=width_label,
                               anchor="w", font=FONT)
            lbl.pack(side="left")
            if tooltip:
                Tooltip(lbl, tooltip)
        elif tooltip:
            self._tt_after = tooltip  # подешевле: tooltip вешается снаружи
        self.entry = ctk.CTkEntry(self, font=FONT_MONO, height=30,
                                  placeholder_text=placeholder or None)
        self.entry.pack(side="left", fill="x", expand=True, padx=4)
        if self.var.get():
            self.entry.insert(0, self.var.get())
        self.entry.bind("<KeyRelease>", self._on_edit)
        self.entry.bind("<FocusOut>", self._on_edit)
        for seq in ("<<Paste>>", "<<Cut>>", "<<Clear>>"):
            try:
                self.entry.bind(seq, lambda e: self.after(1, self._on_edit))
            except Exception:
                pass
        # 01.10: подсказка и на поле, не только на метке
        if tooltip:
            Tooltip(self.entry, tooltip)
        # 21.10: правый клик — Копировать/Вставить/Очистить в любом поле
        attach_clip_menu(self.entry, on_change=self._on_edit)

    def _autosave(self, *_):
        self.cfg.set(self.key, self.var.get())

    def _on_edit(self, _e=None):
        try:
            v = self.entry.get()
        except Exception:
            return
        if v != self.var.get():
            self.var.set(v)

    def _sync_entry(self, *_):
        v = self.var.get()
        try:
            if self.entry.get() != v:
                self.entry.delete(0, "end")
                if v:
                    self.entry.insert(0, v)
        except Exception:
            pass

    def get(self):
        # 24.10: забираем и то, что ввели мышью/вставкой без KeyRelease
        self._on_edit()
        return self.var.get().strip()

    def set(self, v):
        self.var.set(v)
        self.cfg.set(self.key, v)


class CheckField(ctk.CTkCheckBox):
    """Чекбокс с сохранением состояния."""

    def __init__(self, master, label, key, cfg, default=False, tooltip=None):
        self.key = key
        self.cfg = cfg
        value = cfg.get(key, default)
        # 24.10: в JSON может оказаться строка «false» — bool("false")
        # дал бы True, поэтому разбираем строки явно
        if isinstance(value, str):
            value = value.strip().lower() not in ("", "false", "0", "no")
        self.var = tk.BooleanVar(value=bool(value))
        super().__init__(master, text=label, variable=self.var,
                         command=self._save, font=FONT,
                         checkbox_width=20, checkbox_height=20,
                         # 24.10: галочка в акценте палитры, не в синем CTk
                         fg_color=("#7c3aed", "#8b5cf6"),
                         hover_color=("#6d28d9", "#7c3aed"),
                         border_color=("#c9c3e6", "#4b4566"),
                         checkmark_color="#ffffff")
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
    под фактическую ширину блока (раньше wraplength был фиксированным).
    24.10: карточка с акцентным заголовком и тонкой рамкой."""

    def __init__(self, master, text):
        super().__init__(master, fg_color=("#f7f5fe", "#211e2e"),
                         border_width=1, border_color=("#e6defb", "#332c4d"),
                         corner_radius=12)
        self.pack(fill="x", pady=(0, 12))
        lbl = ctk.CTkLabel(self, text="Как это работает",
                           font=("Segoe UI", 12, "bold"),
                           text_color=("#6d28d9", "#c4b5fd"),
                           anchor="w")
        lbl.pack(fill="x", padx=14, pady=(10, 0))
        self._body = ctk.CTkLabel(self, text=text, justify="left", anchor="w",
                                  font=FONT_SMALL, wraplength=900)
        self._body.pack(fill="x", padx=14, pady=(2, 12))
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        # padx=14 с обеих сторон; на узком окне текст больше не обрезается
        wl = max(200, event.width - 28)
        if self._body.cget("wraplength") != wl:
            self._body.configure(wraplength=wl)


class Section(ctk.CTkFrame):
    """Карточка с заголовком и внутренней рамкой. Использование:
    s = Section(parent, 'Заголовок'); виджеты пакуют в s.inner.
    (совместимость: вкладки правятся на s.inner)

    24.10: карточка по стандарту — светлая/тёмная пара цветов, тонкая
    рамка, скругление 12, заголовок отдельной строкой."""

    def __init__(self, master, title, padding=14, subtitle=None):
        super().__init__(master, fg_color=("#ffffff", "#1a1d24"),
                         border_width=1, border_color=("#e3e6ec", "#2a2f3a"),
                         corner_radius=12)
        self.pack(fill="x", pady=(0, 12))
        self._pad = padding
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=padding, pady=(12, 2))
        ctk.CTkLabel(head, text=title, font=("Segoe UI", 13, "bold"),
                     anchor="w").pack(side="left")
        if subtitle:
            ctk.CTkLabel(head, text=subtitle, font=FONT_SMALL,
                         text_color=("gray40", "gray55"), anchor="w").pack(
                side="left", padx=(10, 0))
        self.inner = ctk.CTkFrame(self, fg_color="transparent")
        self.inner.pack(fill="x", padx=padding, pady=(0, padding))


def button_row(master, pady=(2, 0)):
    """Строка кнопок одного смысла: подготовка, боевые команды и т.п."""
    row = ctk.CTkFrame(master, fg_color="transparent")
    row.pack(fill="x", pady=pady)
    return row


# 24.10: семантика цвета кнопок. Пары (светлая, тёмная) — CTk сам
# выбирает нужную при смене темы, перекрашивать вручную не нужно.
ACTION_STYLES = {
    # безопасная проверка без записи
    "safe": {"fg": ("#059669", "#10b981"),
             "hover": ("#047857", "#059669"),
             "text": "#ffffff"},
    # обычный запуск (по умолчанию dry-run)
    "primary": {"fg": ("#7c3aed", "#8b5cf6"),
                "hover": ("#6d28d9", "#7c3aed"),
                "text": "#ffffff"},
    # реальная запись/удаление/откат
    "danger": {"fg": ("#dc2626", "#ef4444"),
               "hover": ("#b91c1c", "#dc2626"),
               "text": "#ffffff"},
    # служебные действия
    "neutral": {"fg": ("#e5e7eb", "#2a2f3a"),
                "hover": ("#d1d5db", "#3b4250"),
                "text": ("#111827", "#e5e7eb")},
}


class ActionButton(ctk.CTkButton):
    """Кнопка действия с семантическим цветом и фиксированным размером.

    kind: safe (зелёная проверка), primary (акцент), danger (запись),
    neutral (служебная). Для кнопок, которые пишут файлы, вызывайте
    link_danger(var_чекбокса «Применить»): пока галочка снята кнопка
    акцентная, при включении становится красной."""

    def __init__(self, master, text, command, tooltip=None, kind="primary",
                 width=235, height=34):
        style = ACTION_STYLES.get(kind, ACTION_STYLES["primary"])
        super().__init__(master, text=text, command=command,
                         width=width, height=height,
                         font=("Segoe UI", 12, "bold"),
                         fg_color=style["fg"], hover_color=style["hover"],
                         text_color=style["text"], corner_radius=8,
                         cursor="hand2")
        self._base_kind = kind
        self._danger_var = None
        self.pack(anchor="w", pady=(8, 0))
        if tooltip:
            Tooltip(self, tooltip)

    # 24.10: цвет кнопки следует за чекбоксом реальной записи.
    # invert=True — опасность при СНЯТОЙ галочке (например «Только отчёт»
    # включён = безопасно, выключен = реальная запись).
    def link_danger(self, var, invert=False):
        self._danger_var = var
        self._danger_invert = invert
        try:
            var.trace_add("write", lambda *_: self._sync_danger())
        except Exception:
            pass
        self._sync_danger()
        return self

    def _sync_danger(self):
        if self._danger_var is None:
            return
        on = bool(self._danger_var.get())
        risky = (not on) if getattr(self, "_danger_invert", False) else on
        self.set_kind("danger" if risky else self._base_kind)

    def set_kind(self, kind):
        """Явная смена семантики (когда опасность зависит от двух галочек)."""
        style = ACTION_STYLES.get(kind, ACTION_STYLES["primary"])
        try:
            self.configure(fg_color=style["fg"], hover_color=style["hover"],
                           text_color=style["text"])
        except Exception:
            pass


# 24.10: прежнее имя оставлено — вкладки и обход кнопок используют его
BigButton = ActionButton

class LogPanel(ctk.CTkFrame):
    """Журнал вывода: поиск с подсветкой, умный автоскролл, масштаб.

    24.10: по стандарту окно вывода стало отдельной вкладкой с
    инструментами. Текст только для чтения, вставка идёт через append().
    Автоскролл следует за выводом, пока пользователь стоит у низа;
    прокрутка вверх останавливает слежение, возврат вниз включает снова.
    """

    TAGS = ("ok", "warn", "err", "cmd", "dim", "found")

    def __init__(self, master, cfg, on_save_report=None):
        super().__init__(master, fg_color=("gray92", "gray14"),
                         corner_radius=12)
        self.cfg = cfg
        self.on_save_report = on_save_report
        self._follow = True
        self._follow_job = None
        self._query = ""
        try:
            size = int(cfg.get("ui.log_font", 11))
        except Exception:
            size = 11
        self._font_size = max(8, min(24, size))
        # 24.10: ограничение журнала, чтобы долгие сканы не съедали память
        try:
            limit = int(cfg.get("ui.log_limit", 5000))
        except Exception:
            limit = 5000
        self._max_lines = max(500, min(100000, limit)) if limit else 5000
        self._font = ctk.CTkFont(family="Consolas", size=self._font_size)
        self._build()

    # --- сборка ---

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 2))

        self.search_var = tk.StringVar()
        self.search = ctk.CTkEntry(top, textvariable=self.search_var,
                                   placeholder_text="Поиск в журнале…",
                                   height=30, width=280, font=FONT)
        self.search.pack(side="left")
        self.search.bind("<Return>", lambda e: self.run_search())
        self.search.bind("<Escape>", lambda e: self.clear_search())
        Tooltip(self.search, "Поиск по тексту журнала без учёта регистра. "
                             "Enter — подсветить все вхождения, Esc — сброс.")

        b_find = ctk.CTkButton(top, text="Найти", width=76, height=30,
                               font=FONT, command=self.run_search,
                               **SMALL_BUTTON)
        b_find.pack(side="left", padx=(6, 0))
        b_reset = ctk.CTkButton(top, text="Сброс", width=70, height=30,
                                font=FONT, command=self.clear_search,
                                **SMALL_BUTTON)
        b_reset.pack(side="left", padx=(4, 0))
        Tooltip(b_reset, "Снять подсветку поиска и очистить строку.")

        self.search_label = ctk.CTkLabel(top, text="", font=FONT_SMALL,
                                         text_color=("gray40", "gray55"))
        self.search_label.pack(side="left", padx=(10, 0))

        b_plus = ctk.CTkButton(top, text="А+", width=38, height=30, font=FONT,
                               command=lambda: self.zoom(1), **SMALL_BUTTON)
        b_plus.pack(side="right")
        Tooltip(b_plus, "Крупнее шрифт журнала. Размер запоминается.")
        self.zoom_label = ctk.CTkLabel(top, text=str(self._font_size),
                                       font=FONT_SMALL, width=26)
        self.zoom_label.pack(side="right", padx=2)
        b_minus = ctk.CTkButton(top, text="А-", width=38, height=30, font=FONT,
                                command=lambda: self.zoom(-1), **SMALL_BUTTON)
        b_minus.pack(side="right")
        Tooltip(b_minus, "Мельче шрифт журнала. Размер запоминается.")

        tools = ctk.CTkFrame(self, fg_color="transparent")
        tools.pack(fill="x", padx=12, pady=(2, 4))
        b_clear = ctk.CTkButton(tools, text="Очистить", width=90, height=28,
                                font=FONT_SMALL, command=self.clear,
                                **SMALL_BUTTON)
        b_clear.pack(side="left")
        Tooltip(b_clear, "Очистить окно вывода (файлы не затрагиваются).")
        b_copy = ctk.CTkButton(tools, text="Копировать всё", width=120,
                               height=28, font=FONT_SMALL,
                               command=self.copy_all, **SMALL_BUTTON)
        b_copy.pack(side="left", padx=6)
        Tooltip(b_copy, "Скопировать весь журнал в буфер обмена.")
        b_rep = ctk.CTkButton(tools, text="Отчёт", width=80, height=28,
                              font=FONT_SMALL, command=self.save_report,
                              **SMALL_BUTTON)
        b_rep.pack(side="left")
        Tooltip(b_rep, "Сохранить журнал в файл (reports/ или выбранная папка).")
        ctk.CTkLabel(tools, text="Ctrl+F — поиск, Ctrl+S — сохранить "
                                 "настройки",
                     font=FONT_SMALL, text_color=("gray45", "gray55"),
                     anchor="e").pack(side="right")

        self.text = ctk.CTkTextbox(self, wrap="word", font=self._font,
                                   corner_radius=10, border_width=1,
                                   border_color=("#e3e6ec", "#2a2f3a"),
                                   activate_scrollbars=True)
        self.text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.text.configure(state="disabled")
        for seq in ("<Configure>", "<MouseWheel>", "<ButtonRelease-1>",
                    "<KeyRelease>"):
            try:
                self.text.bind(seq, lambda e: self._schedule_follow())
            except Exception:
                pass
        self._init_tags()

    def _init_tags(self):
        try:
            self.text.tag_config("found", background="#fde68a",
                                 foreground="#111827")
        except Exception:
            pass

    # --- вид ---

    def apply_theme(self, p):
        """Перекраска нестандартных частей: полотно, курсор, выделение, теги."""
        try:
            self.text.configure(
                fg_color=p["log_bg"], text_color=p["log_fg"],
                border_color=("#e3e6ec", "#2a2f3a"),
                scrollbar_button_color=p["seg_fg"],
                scrollbar_button_hover_color=p["accent"])
            inner = getattr(self.text, "_textbox", None)
            if inner is not None:
                inner.configure(selectbackground=p["sel"],
                                selectforeground=p["log_fg"],
                                insertbackground=p["insert"])
            self.text.tag_config("ok", foreground=p["ok"])
            self.text.tag_config("warn", foreground=p["warn"])
            self.text.tag_config("err", foreground=p["err"])
            self.text.tag_config("cmd", foreground=p["accent"])
            self.text.tag_config("dim", foreground=p["dim"])
        except Exception:
            pass

    # --- вывод ---

    def _schedule_follow(self):
        try:
            if self._follow_job:
                self.after_cancel(self._follow_job)
            self._follow_job = self.after(10, self._sync_follow)
        except Exception:
            pass

    def _sync_follow(self):
        self._follow_job = None
        try:
            self._follow = self.text.yview()[1] > 0.998
        except Exception:
            pass

    def _limit(self):
        """24.10: лимит читается на каждой вставке, чтобы настройка
        «Строк в журнале» применялась без перезапуска."""
        try:
            limit = int(self.cfg.get("ui.log_limit", 5000) or 5000)
        except Exception:
            limit = 5000
        return max(500, min(100000, limit))

    def append(self, text, tag=None):
        if not text:
            return
        try:
            # 24.10: если пользователь вернулся вниз перетаскиванием
            # полосы прокрутки, событий мыши у текста может не быть —
            # проверяем фактическое положение перед вставкой
            if not self._follow:
                try:
                    self._follow = self.text.yview()[1] > 0.998
                except Exception:
                    pass
            state = self.text.cget("state")
            if state == "disabled":
                self.text.configure(state="normal")
            if tag:
                self.text.insert("end", text, tag)
            else:
                self.text.insert("end", text)
            # 24.10: старые строки сверх лимита убираем из окна
            try:
                max_lines = self._limit()
                total = int(self.text.index("end-1c").split(".")[0])
                if total > max_lines + 300:
                    self.text.delete("1.0", f"{total - max_lines + 1}.0")
            except Exception:
                pass
            if state == "disabled":
                self.text.configure(state="disabled")
            if self._follow:
                self.text.see("end")
        except Exception:
            pass

    def get_text(self):
        try:
            return self.text.get("1.0", "end").rstrip()
        except Exception:
            return ""

    def clear(self):
        try:
            state = self.text.cget("state")
            if state == "disabled":
                self.text.configure(state="normal")
            self.text.delete("1.0", "end")
            if state == "disabled":
                self.text.configure(state="disabled")
            self.clear_search()
            self.search_label.configure(text="журнал очищен")
        except Exception:
            pass

    def copy_all(self):
        data = self.get_text()
        if not data:
            self.search_label.configure(text="журнал пуст")
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(data)
            self.search_label.configure(text="скопировано в буфер")
        except Exception:
            pass

    def save_report(self):
        if self.on_save_report:
            self.on_save_report(self.get_text())

    # --- поиск ---

    def run_search(self):
        q = self.search_var.get().strip()
        self._query = q
        try:
            self.text.tag_remove("found", "1.0", "end")
        except Exception:
            return
        if not q:
            self.search_label.configure(text="")
            return
        count = 0
        start = "1.0"
        first = None
        try:
            while True:
                pos = self.text.search(q, start, stopindex="end", nocase=True)
                if not pos:
                    break
                end = f"{pos}+{len(q)}c"
                self.text.tag_add("found", pos, end)
                if first is None:
                    first = pos
                start = end
                count += 1
            self.text.tag_raise("found")
            if first:
                self.text.see(first)
        except Exception:
            pass
        self.search_label.configure(
            text=f"найдено: {count}" if count else "не найдено")

    def clear_search(self):
        self._query = ""
        try:
            self.text.tag_remove("found", "1.0", "end")
        except Exception:
            pass
        try:
            self.search_var.set("")
        except Exception:
            pass
        self.search_label.configure(text="")

    def focus_search(self):
        try:
            self.search.focus_set()
            self.search.select_range(0, "end")
        except Exception:
            pass

    # --- масштаб ---

    def zoom(self, delta):
        self._font_size = max(8, min(24, self._font_size + delta))
        try:
            self._font.configure(size=self._font_size)
            self.zoom_label.configure(text=str(self._font_size))
            self.cfg.set("ui.log_font", self._font_size)
        except Exception:
            pass
