"""textools GUI на CustomTkinter. 18.09: полная переделка UI.
Запуск: textools_gui.bat (pythonw) или python gui_ctk.pyw
Все операции с записью по умолчанию в dry-run; реальная запись —
только через чекбокс «Применить изменения»."""
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import os
os.chdir(HERE)

REPORTS_DIR = HERE / "reports"
HISTORY_FILE = HERE / "logs" / "history.log"  # 01.10: история операций
STOP_FILE = HERE / "stop.flag"  # 01.10: мягкая остановка (совпадает с core.text_parser)


def _log_history(detail):
    """02.10: строка в журнал операций logs/history.log.

    Любая ошибка записи глушится — журнал никогда не мешает работе GUI."""
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {detail}\n")
    except Exception:
        pass

# 22.09: единая палитра GUI (CTk не использует gui_theme.py)
PALETTE = {
    "light": {
        "accent": "#7c3aed", "accent_hover": "#6d28d9",
        "window": "#f4f5f7", "card": "#ffffff", "help_bg": "#f5f2fd",
        "log_bg": "#fbfbf8", "log_fg": "#111827", "insert": "#111827",
        "sel": "#c4b5fd", "dim": "#6b7280",
        "ok": "#059669", "warn": "#b45309", "err": "#dc2626",
        "seg_fg": "#ece9f7", "seg_text": "#4b446b",
    },
    "dark": {
        "accent": "#8b5cf6", "accent_hover": "#7c3aed",
        "window": "#111318", "card": "#1a1d24", "help_bg": "#221f33",
        "log_bg": "#0d0f13", "log_fg": "#d1d5db", "insert": "#e5e7eb",
        "sel": "#3b2d5c", "dim": "#9ca3af",
        "ok": "#34d399", "warn": "#fbbf24", "err": "#f87171",
        "seg_fg": "#23262e", "seg_text": "#c9c2e8",
    },
}


def _pal(dark=None):
    if dark is None:
        dark = ctk.get_appearance_mode().lower() == "dark"
    return PALETTE["dark" if dark else "light"]

from gui_config import CFG
from widgets_ctk import (Tooltip, FONT, FONT_SMALL, FONT_MONO, BigButton,
                         enable_dnd)

# тема из конфига до построения окна
_appearance = "dark" if str(CFG.get("theme", "dark")).lower() == "dark" else "light"
ctk.set_appearance_mode(_appearance)


class Runner:
    """Запускает команду в фоновом потоке, вывод идёт в очередь."""

    def __init__(self, log_fn, done_fn, root):
        self.log_fn = log_fn
        self.done_fn = done_fn
        self.root = root
        self.proc = None
        self.q = queue.Queue()
        self.running = False
        # 22.09: прогресс-бар (присваивается из App, может быть None)
        self.progress_bar = None

    def run(self, cmd, cwd=None):
        if self.running:
            self.log_fn("Уже запущено — дождитесь окончания или нажмите Стоп.\n")
            return
        self.running = True
        self.q = queue.Queue()
        threading.Thread(target=self._worker, args=(cmd, cwd), daemon=True).start()
        self.root.after(100, self._poll)

    def _worker(self, cmd, cwd):
        from gui_config import CFG
        if str(CFG.get("show_cmd", "true")).lower() not in ("false", "0", "no"):
            self.q.put(f"> {' '.join(cmd)}\n\n")
        else:
            self.q.put("> (команда скрыта в настройках)\n\n")
        _log_history(f"START | {' '.join(str(c) for c in cmd)}")
        t0 = time.monotonic()
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                cwd=cwd, creationflags=subprocess.CREATE_NO_WINDOW,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            for line in iter(self.proc.stdout.readline, ""):
                self.q.put(line)
            self.proc.stdout.close()
            code = self.proc.wait()
            self.q.put(f"\n[завершено, код {code}]\n")
            _log_history(f"DONE  | код {code} | {time.monotonic() - t0:.1f} с")
        except Exception as e:
            self.q.put(f"\n[ошибка запуска: {e}]\n")
            _log_history(f"DONE  | ошибка запуска: {e}")
        self.q.put(None)

    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                if item is None:
                    self.running = False
                    # 01.10: сброс флага мягкой остановки и прогресс-бара
                    try:
                        STOP_FILE.unlink(missing_ok=True)
                    except Exception:
                        pass
                    if self.progress_bar is not None:
                        self.progress_bar.set(0)
                    if self.progress_label is not None:
                        self.progress_label.configure(text="")
                    self.done_fn()
                    return
                # 22.09: PROGRESS:N/M — обновление прогресс-бара вместо лога
                # 01.10: рядом с баром счётчик «N/M (x%)»
                m = re.match(r"^PROGRESS:(\d+)/(\d+)", item)
                if m and self.progress_bar is not None:
                    done, total = int(m.group(1)), int(m.group(2))
                    frac = done / total if total > 0 else 0
                    self.progress_bar.set(frac)
                    if self.progress_label is not None:
                        self.progress_label.configure(
                            text=f"{done}/{total} ({frac:.0%})")
                    continue
                self.log_fn(item)
        except queue.Empty:
            pass
        if self.running:
            self.root.after(100, self._poll)

    def stop(self):
        if self.proc and self.running:
            # 01.10: мягкая остановка — кладём stop.flag; инструменты
            # сами завершаются между файлами. Через 3 с — kill как fallback
            # (раньше kill сразу рисковал побить docx в момент записи)
            try:
                STOP_FILE.write_text("stop", encoding="utf-8")
                self.log_fn("\n[остановка: жду окончания текущего файла…]\n")
            except Exception:
                pass

            def _force():
                import time as _t
                for _ in range(30):
                    _t.sleep(0.1)
                    if not self.running:
                        return
                try:
                    self.proc.kill()
                    self.log_fn("\n[остановлено принудительно]\n")
                except Exception:
                    pass

            threading.Thread(target=_force, daemon=True).start()


def run_cmd(cmd):
    # 03.10: дружелюбное сообщение, если внешний скрипт не найден
    # (в т.ч. дефолтный путь вроде C:\AgentLetta\scripts\clean_text_files.py)
    if len(cmd) > 2 and cmd[0] == "python" and not cmd[1].startswith("-"):
        from pathlib import Path as _P
        if not _P(cmd[1]).is_file():
            _app.log_line(
                f"Скрипт не найден: {cmd[1]}\n"
                "Укажите правильный путь на вкладке «Настройки» "
                "(раздел «Пути к внешним скриптам»).\n", "err")
            return
    _app.runner.run(cmd)


def run_internal(modname, args):
    code = (f"import sys; sys.path.insert(0, r'{HERE}'); "
            f"from tools.{modname} import main; main({args!r})")
    _app.runner.run(["python", "-c", code])


_app = None


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        global _app
        _app = self
        # 01.10: подчищаем забытый флаг прошлой сессии
        try:
            STOP_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        # 02.10: drag&drop путей (до построения полей; без библиотеки — тихо)
        try:
            enable_dnd(self)
        except Exception:
            pass

        self.title("textools — текстовые инструменты")
        self.geometry("1100x800")
        self.minsize(900, 640)

        self.runner = Runner(self.log_line, self._on_done, self)

        # --- Верхняя панель ---
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 0))
        ctk.CTkLabel(top, text="textools",
                     font=("Segoe UI", 20, "bold")).pack(side="left")
        ctk.CTkLabel(top, text="  текстовые инструменты",
                     font=FONT).pack(side="left")

        self.theme_var = tk.StringVar(value=_appearance)
        tb = ctk.CTkSegmentedButton(top, values=["light", "dark"],
                                    command=self._on_theme_change,
                                    height=28)
        tb.set(_appearance)
        tb.pack(side="right")
        # 18.09: CTkSegmentedButton.bind не работает — Tooltip на внутренние кнопки
        for ch in tb.winfo_children():
            try:
                Tooltip(ch, "Светлая или тёмная тема. Выбор сохраняется.")
            except Exception:
                pass
        ctk.CTkLabel(top, text="Тема:", font=FONT_SMALL).pack(
            side="right", padx=(0, 6))

        # 22.09: акцентные сегменты (тема + вкладки)
        p = _pal()
        tb.configure(
            fg_color=p["seg_fg"], selected_color=p["accent"],
            selected_hover_color=p["accent_hover"],
            unselected_color=p["card"], unselected_hover_color=p["card"],
            text_color=p["seg_text"], text_color_disabled=p["dim"])

        # --- Вкладки ---
        # 22.09: акцентный сегмент вкладок
        self.nb = ctk.CTkTabview(self, anchor="nw",
                                 segmented_button_fg_color=p["seg_fg"],
                                 segmented_button_selected_color=p["accent"],
                                 segmented_button_selected_hover_color=p["accent_hover"],
                                 segmented_button_unselected_color=p["seg_fg"],
                                 segmented_button_unselected_hover_color=p["card"],
                                 text_color=p["seg_text"])
        self.nb.pack(fill="both", expand=True, padx=16, pady=(10, 0))
        self._theme_segment = tb

        # --- Лог ---
        log_frame = ctk.CTkFrame(self, fg_color=("gray92", "gray14"),
                                 corner_radius=8)
        log_frame.pack(fill="both", expand=True, padx=16, pady=10)
        ctk.CTkLabel(log_frame, text="Вывод (результат работы инструмента)",
                     font=("Segoe UI", 12, "bold"), anchor="w").pack(
            fill="x", padx=12, pady=(8, 2))

        # 22.09: прогресс-бар (для долгих сканов)
        # 01.10: строка прогресса — бар + ярлык «N/M (x%)»
        prog_row = ctk.CTkFrame(log_frame, fg_color="transparent")
        prog_row.pack(fill="x", padx=12, pady=(0, 2))
        self.progress_bar = ctk.CTkProgressBar(prog_row, height=8,
                                               progress_color=p["accent"])
        self.progress_bar.set(0)
        self.progress_bar.pack(side="left", fill="x", expand=True)
        self.progress_label = ctk.CTkLabel(prog_row, text="", font=FONT_SMALL,
                                           width=150, anchor="e")
        self.progress_label.pack(side="left", padx=(10, 0))
        self.runner.progress_bar = self.progress_bar
        self.runner.progress_label = self.progress_label
        self.runner.status_fn = (lambda: self.status.configure(
            text="выполняется…"))

        # tk.Text для лога (цветные теги) + свой скроллбар
        # 22.09: начальные цвета из палитры
        log_inner = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_inner.pack(fill="both", expand=True, padx=12)
        self.log = tk.Text(log_inner, height=8, wrap="word",
                           font=FONT_MONO, borderwidth=0, relief="flat",
                           bg=p["log_bg"], fg=p["log_fg"],
                           insertbackground=p["insert"],
                           selectbackground=p["sel"])
        log_sb = ctk.CTkScrollbar(log_inner, command=self.log.yview)
        self.log.configure(yscrollcommand=log_sb.set)
        log_sb.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)
        self._apply_log_theme()

        btns = ctk.CTkFrame(log_frame, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=(6, 10))
        # 22.09: компактные кнопки с фиолетовым ховером
        stop_b = ctk.CTkButton(btns, text="Стоп", width=70, height=28,
                               fg_color=("gray75", "gray30"),
                               hover_color=_pal()["accent"],
                               command=self.runner.stop)
        stop_b.pack(side="left")
        Tooltip(stop_b, "Мягко остановить операцию: программа завершает "
                        "текущий файл и корректно заканчивает работу.")
        rep_b = ctk.CTkButton(btns, text="Отчёт", width=70, height=28,
                              fg_color=("gray75", "gray30"),
                              hover_color=_pal()["accent"],
                              command=self._save_report)
        rep_b.pack(side="left", padx=6)
        Tooltip(rep_b, "Сохранить содержимое окна вывода в файл "
                       "(reports/ или выбранная папка).")
        clr_b = ctk.CTkButton(btns, text="Очистить", width=80, height=28,
                              fg_color=("gray75", "gray30"),
                              hover_color=_pal()["accent"],
                              command=lambda: self.log.delete("1.0", "end"))
        clr_b.pack(side="left")
        Tooltip(clr_b, "Очистить окно вывода (файлы не затрагиваются).")
        self._compact_btns = (stop_b, rep_b, clr_b)
        self.status = ctk.CTkLabel(btns, text="готов", font=FONT_SMALL)
        self.status.pack(side="right")

        # --- Вкладки инструментов ---
        from tabs_names import NamesTab
        from tabs_vault import VaultTab
        from tabs_clean import CleanTab
        from tabs_replace import ReplaceTab
        from tabs_settings import SettingsTab

        for cls in (NamesTab, VaultTab, CleanTab, ReplaceTab, SettingsTab):
            tab = self.nb.add(cls.LABEL)
            # скролл-контейнер вкладки
            scroll = ctk.CTkScrollableFrame(self.nb.tab(cls.LABEL),
                                            fg_color="transparent")
            scroll.pack(fill="both", expand=True)
            t = cls(scroll)
            t._build(t)
            t.pack(fill="x", anchor="n")

    # --- Тема ---

    def _on_theme_change(self, value):
        ctk.set_appearance_mode(value)
        CFG.set("theme", value)
        self._apply_log_theme()
        # 22.09: перекраска акцентных элементов при смене темы
        p = _pal()
        self._theme_segment.configure(
            fg_color=p["seg_fg"], selected_color=p["accent"],
            selected_hover_color=p["accent_hover"],
            unselected_color=p["card"], unselected_hover_color=p["card"],
            text_color=p["seg_text"], text_color_disabled=p["dim"])
        self.nb.configure(
            segmented_button_fg_color=p["seg_fg"],
            segmented_button_selected_color=p["accent"],
            segmented_button_selected_hover_color=p["accent_hover"],
            segmented_button_unselected_color=p["seg_fg"],
            segmented_button_unselected_hover_color=p["card"],
            text_color=p["seg_text"])
        for b in self._compact_btns:
            b.configure(hover_color=p["accent"])
        # 01.10: крупные кнопки тоже перекрашиваются (раньше держали цвет
        # темы на момент создания)
        self._restyle_big_buttons(p)

    def _restyle_big_buttons(self, p):
        def walk(w):
            yield w
            for c in w.winfo_children():
                yield from walk(c)
        for frame in self.nb._tab_dict.values():
            for w in walk(frame):
                if isinstance(w, BigButton):
                    w.configure(fg_color=p["accent"],
                                hover_color=p["accent_hover"])

    def _apply_log_theme(self):
        # 22.09: цвета из единой палитры
        p = _pal()
        self.progress_bar.configure(progress_color=p["accent"])
        self.log.configure(
            bg=p["log_bg"], fg=p["log_fg"],
            insertbackground=p["insert"],
            selectbackground=p["sel"])
        self.log.tag_configure("ok", foreground=p["ok"])
        self.log.tag_configure("warn", foreground=p["warn"])
        self.log.tag_configure("err", foreground=p["err"])
        self.log.tag_configure("cmd", foreground=p["accent"],
                               font=(FONT_MONO[0], 11, "bold"))
        self.log.tag_configure("dim", foreground=p["dim"])

    # --- Лог и статус ---

    def log_line(self, text, tag=None):
        if tag:
            self.log.insert("end", text, tag)
        else:
            self.log.insert("end", text)
        self.log.see("end")

    def _on_done(self):
        self.status.configure(text="готов")

    def _save_report(self):
        text = self.log.get("1.0", "end").rstrip()
        if not text:
            return
        REPORTS_DIR.mkdir(exist_ok=True)
        pth = filedialog.asksaveasfilename(
            initialdir=str(REPORTS_DIR), defaultextension=".txt",
            filetypes=[("Текст", "*.txt"), ("Markdown", "*.md")])
        if pth:
            Path(pth).write_text(text, encoding="utf-8")
            self.log_line("Отчёт сохранён: ", "ok")
            self.log_line(f"{pth}\n")


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()