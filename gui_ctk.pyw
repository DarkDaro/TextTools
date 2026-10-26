"""textools GUI на CustomTkinter. 18.09: полная переделка UI.
Запуск: textools_gui.bat (pythonw) или python gui_ctk.pyw
Все операции с записью по умолчанию в dry-run; реальная запись —
только через чекбокс «Применить изменения».

24.10: интерфейс приведён к общему UI-стандарту (UI_DESIGN.md):
шапка с акцентной полосой, статусбар над вкладками, вкладка «Журнал»
с поиском и масштабом, семантические кнопки, горячие клавиши,
сохранение геометрии окна и последней вкладки."""
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
try:
    import winsound  # 21.10: системные звуки ошибок и уведомлений
except Exception:
    winsound = None
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import os
# 26.10: режим PyInstaller one-file (exe): BUNDLE_DIR — распакованные
# пакеты во временном _MEIPASS (read-only), APP_DIR — папка рядом с exe:
# конфиг, логи, отчёты, stop.flag живут там и переживают перезапуски.
if getattr(sys, "frozen", False):
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", str(HERE)))
    APP_DIR = Path(sys.executable).parent
else:
    BUNDLE_DIR = HERE
    APP_DIR = HERE
os.chdir(APP_DIR)

REPORTS_DIR = APP_DIR / "reports"
HISTORY_FILE = APP_DIR / "logs" / "history.log"  # 01.10: история операций
STOP_FILE = APP_DIR / "stop.flag"  # 01.10: мягкая остановка (совпадает с core.text_parser)
LOG_TAB = "Журнал"


def _log_history(detail):
    """02.10: строка в журнал операций logs/history.log.

    Любая ошибка записи глушится — журнал никогда не мешает работе GUI."""
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {detail}\n")
    except Exception:
        pass


def _log_crash(prefix=""):
    """20.10: трейсбек в logs/gui_crash.log. Под pythonw окно без этого
    просто стоит пустым и причина теряется (как при пустом экране 20.10)."""
    import traceback
    try:
        LOG = APP_DIR / "logs" / "gui_crash.log"  # 26.10: APP_DIR (frozen-safe)
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} "
                    f"{prefix} =====\n")
            traceback.print_exc(file=f)
    except Exception:
        pass


def _log_info(prefix):
    """20.10: маркер старта без трейсбека — что питон, дошло ли до
    построения, mainloop и закрытия."""
    try:
        LOG = APP_DIR / "logs" / "gui_crash.log"  # 26.10: APP_DIR (frozen-safe)
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%H:%M:%S} | {prefix}\n")
    except Exception:
        pass


def _sys_excepthook(exc_type, exc_val, exc_tb):
    _log_crash("runtime")
    sys.__excepthook__(exc_type, exc_val, exc_tb)


def _walk_widgets(w):
    """21.10: обход дерева виджетов (для сбора кнопок и перекраски)."""
    yield w
    for c in w.winfo_children():
        yield from _walk_widgets(c)

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


from gui_config import CFG, CONFIG_FILE
# 26.10: FONT не используется (везде локальные ctk-шрифты), pyflakes — отключён
# from widgets_ctk import (Tooltip, FONT, FONT_SMALL, BigButton,
from widgets_ctk import (Tooltip, FONT_SMALL, BigButton,
                         LogPanel, enable_dnd)

# тема из конфига до построения окна
_appearance = "dark" if str(CFG.get("theme", "dark")).lower() == "dark" else "light"
ctk.set_appearance_mode(_appearance)


def _tool_label(cmd):
    """21.10: короткое имя инструмента для статуса и тостов."""
    if len(cmd) > 2 and str(cmd[1]) == "-c":
        m = re.search(r"tools\.(\w+)", str(cmd[2]))
        if m:
            return m.group(1)
    for a in cmd[1:]:
        s = str(a)
        if s.startswith("-"):
            continue
        try:
            return Path(s).stem or s
        except Exception:
            return s
    return "операция"


def _cfg_flag(key, default=True):
    """21.10: булева настройка из конфига (снивает «false»/«0»/«no»)."""
    v = CFG.get(key, default)
    if isinstance(v, bool):
        return v
    return str(v).lower() not in ("false", "0", "no")


def _toast_beep(level):
    """21.10: короткий системный звук уведомления. Отключается галочкой
    «Звуковые сигналы» на вкладке «Настройки»; ошибки звучат всегда громче."""
    if winsound is None:
        return
    if not _cfg_flag("sound", True):
        return
    flags = {"err": winsound.MB_ICONERROR,
             "warn": winsound.MB_ICONEXCLAMATION,
             "ok": winsound.MB_ICONASTERISK}
    f = flags.get(level)
    if f is not None:
        try:
            winsound.MessageBeep(f)
        except Exception:
            pass


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
        # 20.10: инициализируем заранее — _poll ссылается на оба
        self.progress_label = None
        # 21.10: тосты, имя инструмента, таймер, пометка реального прогресса
        self.notify_fn = None
        self.status_fn = None
        self._label = "операция"
        self._t0 = 0.0
        self._had_progress = False
        self._result = None
        # 24.10: этап и тик из служебных сообщений процесса
        self._stage = ""
        self._tick = 0
        # 24.10: закрытие окна во время запуска и признак остановки
        self._closing = False
        self._stopped = False
        self._run_id = 0

    def run(self, cmd, cwd=None, label=None):
        if self.running:
            # 21.10: защита от второго параллельного запуска — сообщение
            # в лог и всплывающий тост со звуком
            msg = (f"Уже запущено: {self._label}. Дождитесь окончания "
                   "или нажмите «Стоп».")
            self.log_fn(msg + "\n", "warn")
            if self.notify_fn:
                self.notify_fn(msg, "warn")
            return
        self.running = True
        self._closing = False
        self._stopped = False
        self._run_id += 1
        self._label = label or _tool_label(cmd)
        self._t0 = time.monotonic()
        self._had_progress = False
        self._stage = ""
        self._tick = 0
        self._result = None
        self.q = queue.Queue()
        threading.Thread(target=self._worker, args=(cmd, cwd), daemon=True).start()
        if self.status_fn:
            self.status_fn(f"выполняется: {self._label}")
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
            # 24.10: окно закрыли раньше, чем процесс успел стартовать.
            # Кладём stop.flag сразу после запуска, чтобы инструмент
            # завершился между файлами, а не остался сиротой.
            if self._closing:
                try:
                    STOP_FILE.write_text("stop", encoding="utf-8")
                except Exception:
                    pass
            for line in iter(self.proc.stdout.readline, ""):
                self.q.put(line)
            self.proc.stdout.close()
            code = self.proc.wait()
            elapsed = time.monotonic() - t0
            self.q.put(f"\n[завершено, код {code}]\n")
            # 21.10: структурный результат — код выхода и длительность
            # идут через очередь в GUI-поток (тост, звук, статус)
            self.q.put(("result", code, elapsed))
            _log_history(f"DONE  | код {code} | {elapsed:.1f} с | {self._label}")
        except Exception as e:
            self.q.put(f"\n[ошибка запуска: {e}]\n")
            self.q.put(("result", -1, time.monotonic() - t0))
            _log_history(f"DONE  | ошибка запуска: {e} | {self._label}")
        self.q.put(None)

    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                if isinstance(item, tuple) and item and item[0] == "result":
                    self._result = item[1:]
                    continue
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
                    res = self._result if self._result is not None else (0, 0.0)
                    self._result = None
                    self.done_fn(res[0], res[1], self._stopped)
                    return
                # 24.10: служебные сообщения процесса. Старый контракт
                # PROGRESS:N/M сохранён, добавочно читаются @@PROGRESS,
                # @@STAGE и @@TICK (этап и пульс в статусе).
                m = re.match(r"^(?:@@)?PROGRESS[:\s]+(\d+)/(\d+)", item)
                if m and self.progress_bar is not None:
                    done, total = int(m.group(1)), int(m.group(2))
                    frac = done / total if total > 0 else 0
                    self.progress_bar.set(frac)
                    self._had_progress = True
                    if self.progress_label is not None:
                        self.progress_label.configure(
                            text=f"{done}/{total} ({frac:.0%})")
                    continue
                m = re.match(r"^@@STAGE\s+(.+?)\s*$", item)
                if m:
                    self._stage = m.group(1)
                    continue
                m = re.match(r"^@@TICK\s+(\d+)", item)
                if m:
                    self._tick = int(m.group(1))
                    continue
                # 24.10: сбой обработчика строки не должен убивать поток
                # чтения вывода (ошибка видна по пропущенной строке)
                try:
                    self.log_fn(item)
                except Exception:
                    pass
        except queue.Empty:
            pass
        except Exception:
            # 24.10: сбой отрисовки не должен оставлять running=True
            # навсегда; поток уже пишет в очередь, следующий тик догонит
            pass
        if self.running:
            # 21.10: пока движок не присылает PROGRESS (нештатные и внешние
            # скрипты), бар «дышит» пульсом — видна живая работа; в статусе
            # имя инструмента и время
            if not self._had_progress and self.progress_bar is not None:
                t = (time.monotonic() - self._t0) % 2.4
                tri = t if t <= 1.2 else 2.4 - t
                self.progress_bar.set(0.08 + 0.82 * (tri / 1.2))
                if self.progress_label is not None:
                    self.progress_label.configure(text="идёт работа…")
            if self.status_fn:
                s = int(time.monotonic() - self._t0)
                if self._stage:
                    self.status_fn(f"этап «{self._stage}» идёт "
                                   f"{self._tick or s} с…")
                else:
                    self.status_fn(
                        f"выполняется: {self._label} • {s // 60}:{s % 60:02d}")
            self.root.after(100, self._poll)

    def stop(self):
        # 24.10: остановка работает и в окне между «нажал» и «процесс
        # стартовал». Флаг ставится сразу, поток-сторож ждёт до 15 с.
        if not self.running or self._stopped:
            return
        self._stopped = True
        # 01.10: мягкая остановка — кладём stop.flag; инструменты
        # сами завершаются между файлами. 20.10: окно ожидания с
        # 3 до 15 с — долгий docx файла мог быть убит на середине
        # записи (раньше kill сразу рисковал побить файл в момент записи)
        try:
            STOP_FILE.write_text("stop", encoding="utf-8")
            self.log_fn("\n[остановка: жду окончания текущего файла…]\n")
            if self.notify_fn:
                self.notify_fn("Останавливаю операцию — текущий файл "
                               "будет докончен", "warn")
        except Exception:
            pass

        def _force():
            import time as _t
            rid = self._run_id
            # 24.10: ждём полные 15 секунд, чтобы инструмент успел
            # докончить текущий файл. Раньше цикл выходил на первом
            # появлении proc и убивал процесс сразу.
            for _ in range(150):
                _t.sleep(0.1)
                # 24.10: не трогаем следующий запуск, если этот уже кончился
                if self._run_id != rid or not self.running:
                    return
            try:
                if self.proc is not None:
                    self.proc.kill()
                    # 24.10: из потока нельзя трогать Tk — кладём строку
                    # в очередь, её напечатает _poll в главном потоке
                    self.q.put("\n[остановлено принудительно]\n")
            except Exception:
                pass

        threading.Thread(target=_force, daemon=True).start()


def run_cmd(cmd):
    # Дружелюбное сообщение, если внешний скрипт не настроен или не найден.
    # 25.10: подробная подсказка и тост — один раз за сессию на скрипт,
    # дальше короткая строка, чтобы журнал не забивался одинаковым текстом.
    if len(cmd) > 2 and cmd[0] == sys.executable \
            and not cmd[1].startswith("-"):
        from pathlib import Path as _P
        if cmd[1] == "":
            _app.warn_script(
                "external",
                "Внешний скрипт не настроен.\n"
                "Откройте «Настройки» → «Пути к внешним скриптам» "
                "и нажмите «Найти скрипты» (или укажите путь вручную).\n",
                key=("external", tuple(str(x) for x in cmd[2:])))
            return
        script = _P(cmd[1])
        if not script.is_file():
            _app.warn_script(
                script.name,
                f"Скрипт не найден: {cmd[1]}\n"
                "Нажмите «Найти скрипты» на вкладке «Настройки» "
                "или укажите правильный путь вручную.\n",
                key=str(script.resolve()))
            return
        # 26.10 (exe): find_cjk/phrase_check — внутренние скрипты
        # проекта; в frozen-режиме их нельзя запустить как .py-файл,
        # поэтому сам exe перезапускается с --tool-run и вызывает
        # их main(). В обычном запуске путь прежний (python + файл).
        if getattr(sys, "frozen", False):
            base = script.name.lower()
            if base == "find_cjk.py":
                cmd = [sys.executable, "--tool-run", "find_cjk"] + cmd[2:]
            elif base == "phrase_check.py":
                cmd = [sys.executable, "--tool-run", "phrase_check"] + cmd[2:]
    if _app.begin_run():
        _app.runner.run(cmd)


def run_internal(modname, args):
    # 26.10 (exe): в PyInstaller one-file sys.executable — сам exe;
    # кодовая строка "-c" не работает. Заменяем self-run: exe
    # перезапускает себя с --tool-run, main() его разбирает и вызывает
    # tools.<modname>.main(args). В обычном (не frozen) запуске путь
    # прежний: sys.executable -c "...", тот же интерпретатор, что GUI.
    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--tool-run", modname, *args]
    else:
        code = (f"import sys; sys.path.insert(0, r'{HERE}'); "
                f"from tools.{modname} import main; main({args!r})")
        cmd = [sys.executable, "-c", code]
    # 20.10: sys.executable вместо «python» из PATH — при двух питонах
    # на машине (3.14 с пакетами / 3.15 пустой) гарантированно тот же
    # интерпретатор, что питает сам GUI
    if _app.begin_run():
        _app.runner.run(cmd)


_app = None


def tool_cmd(modname, *rest):
    """26.10: единая точка запуска внутренних .py-инструментов
    (find_cjk, phrase_check) как отдельного процесса.
    exe (frozen): [exe, --tool-run, modname, *rest] — сам exe
    разбирает флаг и вызывает main(). Обычный запуск: python + файл."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--tool-run", modname, *rest]
    paths = {"find_cjk": HERE / "find_cjk.py",
             "phrase_check": HERE / "tools" / "phrase_check.py"}
    return [sys.executable, str(paths[modname]), *rest]


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
        self.minsize(900, 640)
        self._restore_geometry()

        # 24.10: состояние вкладок и обход кнопок
        self._tab_guard = False
        self._current_tab = ""
        self._tab_check_job = None
        self._tabs = {}
        self._big_buttons = []
        # 24.10: фоновые задачи вне Runner (витрины, ё/е-аудит)
        self._bg_active = False
        self._bg_label = ""
        self._bg_t0 = 0.0
        self._bg_job = None
        self._bg_proc = None
        # 25.10: чтобы «скрипт не настроен» не повторялось в журнале и тостах
        self._script_warned = set()

        self.runner = Runner(self.log_line, self._on_done, self)
        # 21.10: тосты (всплывающие сообщения) из Runner — «уже запущено» и т.п.
        self.runner.notify_fn = self.toast
        # 20.10: закрытие окна во время работы процесса — останавливаем
        # запись аккуратно, вместо жёсткого обрыва с недописанным файлом
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_header()
        self._build_statusbar()
        self._build_tabs()
        self._collect_big_buttons()
        self._apply_log_theme()
        self._bind_hotkeys()
        # 24.10: восстановление вкладки после первой отрисовки: configure
        # до рендера ломает pack-геометрию (окно 200x200, кнопки мёртвые)
        self.after(300, self._apply_saved_tab)

    # --- построение окна ---

    def _build_header(self):
        p = _pal()
        self._header = ctk.CTkFrame(self, fg_color="transparent")
        self._header.pack(fill="x", padx=16, pady=(12, 0))

        left = ctk.CTkFrame(self._header, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="textools",
                     font=("Segoe UI", 22, "bold")).pack(side="left")
        ctk.CTkLabel(left, text="  текстовые инструменты для авторов",
                     font=FONT_SMALL, text_color=("gray45", "gray55")).pack(
            side="left", padx=(2, 0), pady=(6, 0))

        right = ctk.CTkFrame(self._header, fg_color="transparent")
        right.pack(side="right")

        self.theme_var = tk.StringVar(value=_appearance)
        tb = ctk.CTkSegmentedButton(right, values=["light", "dark"],
                                    command=self._on_theme_change,
                                    width=160, height=28,
                                    dynamic_resizing=False,
                                    font=FONT_SMALL)
        tb.set(_appearance)
        tb.pack(side="right")
        tb.configure(
            fg_color=p["seg_fg"], selected_color=p["accent"],
            selected_hover_color=p["accent_hover"],
            unselected_color=p["card"], unselected_hover_color=p["card"],
            text_color=p["seg_text"], text_color_disabled=p["dim"])
        # 18.09: CTkSegmentedButton.bind не работает — Tooltip на внутренние кнопки
        for ch in tb.winfo_children():
            try:
                Tooltip(ch, "Светлая или тёмная тема. Выбор сохраняется.")
            except Exception:
                pass
        ctk.CTkLabel(right, text="Тема:", font=FONT_SMALL).pack(
            side="right", padx=(0, 6))

        # 24.10: индикатор текущего раздела (аналог индикатора режима)
        self._tab_pill = ctk.CTkLabel(right, text="", height=26,
                                      corner_radius=13, padx=12,
                                      font=("Segoe UI", 11, "bold"),
                                      fg_color=p["accent"],
                                      text_color="#ffffff")
        self._tab_pill.pack(side="right", padx=(0, 10))
        self._theme_segment = tb

        # 24.10: акцентная полоса под шапкой
        self._accent_bar = ctk.CTkFrame(self, height=2,
                                        fg_color=p["accent"],
                                        corner_radius=0)
        self._accent_bar.pack(fill="x", padx=16, pady=(8, 0))

    def _build_statusbar(self):
        """24.10: статус и прогресс над вкладками — на маленьком окне
        не исчезают, как исчезал подвал. «Стоп» всегда под рукой."""
        p = _pal()
        bar = ctk.CTkFrame(self, fg_color=("gray92", "gray14"),
                           corner_radius=8)
        bar.pack(fill="x", padx=16, pady=(8, 0))

        self.status = ctk.CTkLabel(bar, text="готов", font=FONT_SMALL,
                                   anchor="w")
        self.status.pack(side="left", padx=12, pady=7)

        self._stop_btn = ctk.CTkButton(
            bar, text="Стоп", width=70, height=28, font=FONT_SMALL,
            fg_color=("#fee2e2", "#3b1d1d"),
            hover_color=("#fecaca", "#5b2626"),
            text_color=("#991b1b", "#fecaca"),
            state="disabled", command=self.stop_all)
        self._stop_btn.pack(side="right", padx=(6, 10), pady=5)
        Tooltip(self._stop_btn, "Мягко остановить операцию: программа "
                                "завершает текущий файл и корректно "
                                "заканчивает работу.")

        self.progress_label = ctk.CTkLabel(bar, text="", font=FONT_SMALL,
                                           width=120, anchor="e",
                                           text_color=("gray40", "gray60"))
        self.progress_label.pack(side="right", padx=(6, 0), pady=7)

        self.progress_bar = ctk.CTkProgressBar(bar, height=8,
                                               progress_color=p["accent"])
        self.progress_bar.set(0)
        self.progress_bar.pack(side="left", fill="x", expand=True,
                               padx=(8, 0), pady=7)
        self.runner.progress_bar = self.progress_bar
        self.runner.progress_label = self.progress_label
        # 24.10: configure(text=...) — иначе positional-строка уходила
        # в require_redraw, и статус во время работы не обновлялся
        self.runner.status_fn = lambda text: self.status.configure(text=text)

    def _build_tabs(self):
        from tabs_names import NamesTab
        from tabs_vault import VaultTab
        from tabs_clean import CleanTab
        from tabs_replace import ReplaceTab
        from tabs_settings import SettingsTab

        p = _pal()
        self.nb = ctk.CTkTabview(
            self, anchor="nw", command=self._on_tab,
            segmented_button_fg_color=p["seg_fg"],
            segmented_button_selected_color=p["accent"],
            segmented_button_selected_hover_color=p["accent_hover"],
            segmented_button_unselected_color=p["seg_fg"],
            segmented_button_unselected_hover_color=p["card"],
            text_color=p["seg_text"])
        self.nb.pack(fill="both", expand=True, padx=16, pady=(8, 12))

        for cls in (NamesTab, VaultTab, CleanTab, ReplaceTab, SettingsTab):
            tab = self.nb.add(cls.LABEL)
            # скролл-контейнер вкладки
            scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
            scroll.pack(fill="both", expand=True, padx=(4, 8), pady=(4, 8))
            t = cls(scroll, fg_color="transparent")
            t._build(t)
            t.pack(fill="x", anchor="n")
            self._tabs[cls.LABEL] = t

        log_tab = self.nb.add(LOG_TAB)
        self._log_panel = LogPanel(log_tab, CFG,
                                   on_save_report=self._save_report)
        self._log_panel.pack(fill="both", expand=True, padx=6, pady=(6, 8))
        self._tabs[LOG_TAB] = self._log_panel
        self._log_panel.apply_theme(_pal())
        # 24.10: даже без запоминания вкладки индикатор должен быть заполнен
        try:
            self._update_tab_ui(self.nb.get(), save=False)
        except Exception:
            pass

    def _collect_big_buttons(self):
        # 21.10: реестр «крупных» кнопок инструментов — на время операции
        # они блокируются, чтобы нельзя было запустить вторую параллельно
        for frame in self.nb._tab_dict.values():
            for w in _walk_widgets(frame):
                if isinstance(w, BigButton):
                    self._big_buttons.append(w)

    # --- геометрия и состояние ---

    def _restore_geometry(self):
        """24.10: геометрия из конфига с защитой от выхода за экран."""
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        geo = str(CFG.get("ui.geometry", "") or "")
        if not _cfg_flag("remember_geometry", True):
            geo = ""
        m = re.match(r"^(\d+)x(\d+)([+-]\d+)([+-]\d+)$", geo)
        if m:
            w, h, x, y = (int(m.group(1)), int(m.group(2)),
                          int(m.group(3)), int(m.group(4)))
            w = max(900, min(w, sw - 40))
            h = max(640, min(h, sh - 80))
            x = max(0, min(x, sw - w))
            y = max(0, min(y, sh - h))
        else:
            w = min(1120, sw - 40)
            h = min(860, sh - 80)
            x = (sw - w) // 2
            y = max(0, (sh - h) // 2 - 20)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def reset_geometry(self):
        """24.10: вернуть окно в рабочий размер и по центру экрана."""
        try:
            CFG.set("ui.geometry", "")
        except Exception:
            pass
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = min(1120, sw - 40)
        h = min(860, sh - 80)
        x = (sw - w) // 2
        y = max(0, (sh - h) // 2 - 20)
        try:
            self.state("normal")
        except Exception:
            pass
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _apply_saved_tab(self):
        if not _cfg_flag("remember_tab", True):
            return
        name = CFG.get("ui.last_tab", "")
        if isinstance(name, str) and name in self._tabs:
            self._goto_tab(name)

    def _save_ui_state(self):
        try:
            # свернутое окно отдаёт бессмысленный размер, не сохраняем его
            if _cfg_flag("remember_geometry", True) and \
                    self.state() != "iconic":
                CFG.set("ui.geometry", self.geometry())
        except Exception:
            pass
        try:
            if _cfg_flag("remember_tab", True) and self._current_tab:
                CFG.set("ui.last_tab", self._current_tab)
        except Exception:
            pass

    # --- вкладки ---

    def _on_tab(self):
        """Выбор вкладки мышью: обновляем индикатор и запоминаем раздел."""
        if self._tab_guard:
            return
        self._update_tab_ui(self.nb.get())

    def _goto_tab(self, name, save=True):
        """Программный переход: set() не вызывает command вкладки,
        поэтому состояние обновляем явно (как в UI-стандарте)."""
        if name not in self._tabs:
            return
        if self.nb.get() != name:
            self._tab_guard = True
            try:
                self.nb.set(name)
            finally:
                self._tab_guard = False
        self._update_tab_ui(name, save=save)

    def _update_tab_ui(self, name, save=True):
        self._current_tab = name
        try:
            self._tab_pill.configure(text=name)
        except Exception:
            pass
        if save and _cfg_flag("remember_tab", True):
            try:
                CFG.set("ui.last_tab", name)
            except Exception:
                pass
        # 24.10: защита от гонки CTkTabview. При быстрой смене вкладок
        # отложенные grid_forget_all_tabs выполняются в обратном порядке
        # и могут скрыть текущую вкладку (пустое окно). Через 180 мс
        # проверяем, что текущая вкладка снова на месте.
        try:
            if self._tab_check_job:
                self.after_cancel(self._tab_check_job)
            self._tab_check_job = self.after(180, self._ensure_current_tab)
        except Exception:
            pass

    def _ensure_current_tab(self):
        self._tab_check_job = None
        name = self._current_tab
        frame = self.nb._tab_dict.get(name)
        if frame is not None and not frame.winfo_ismapped():
            try:
                self.nb.set(name)
            except Exception:
                pass

    # --- тема ---

    def _on_theme_change(self, value):
        ctk.set_appearance_mode(value)
        CFG.set("theme", value)
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
        self._accent_bar.configure(fg_color=p["accent"])
        self._tab_pill.configure(fg_color=p["accent"])
        self._apply_log_theme()

    def _apply_log_theme(self):
        p = _pal()
        self.progress_bar.configure(progress_color=p["accent"])
        if getattr(self, "_log_panel", None) is not None:
            self._log_panel.apply_theme(p)

    # --- лог и статус ---

    def log_line(self, text, tag=None):
        if tag is None and str(text).startswith("> "):
            tag = "cmd"
        self._log_panel.append(text, tag)

    def warn_script(self, name, message, key=None):
        """25.10: один подробный текст на скрипт за сессию, дальше коротко.

        key — отдельный признак для дедупликации: полный путь, а не имя
        файла, чтобы два разных clean.py не схлопнулись в одно сообщение.
        """
        dedup = key if key is not None else name
        if dedup not in self._script_warned:
            self._script_warned.add(dedup)
            self.log_line(message, "err")
            first = message.splitlines()[0] if message else "Скрипт недоступен"
            self.toast(first, "err")
        else:
            self.log_line(f"{name}: скрипт недоступен (см. «Настройки»).\n",
                          "warn")

    # 21.10: активные тосты — новые выстраиваются стопкой выше предыдущих
    _toast_stack = []

    def toast(self, text, level="info", beep=True):
        """21.10: всплывающее сообщение справа снизу экрана, исчезает само
        (или по клику). beep=False — без звука (звук тогда прозвучит
        отдельно, например «Готово» при выключенном тосте завершения)."""
        try:
            if beep:
                _toast_beep(level)
            p = _pal()
            border = {"ok": p["ok"], "warn": p["warn"], "err": p["err"],
                      "info": p["accent"]}.get(level, p["accent"])
            win = tk.Toplevel(self)
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            outer = tk.Frame(win, bg=border, padx=2, pady=2)
            outer.pack()
            inner = tk.Frame(win, bg=p["card"], padx=14, pady=9)
            inner.pack()
            tk.Label(inner, text=text, justify="left", bg=p["card"],
                     fg=p["log_fg"], font=("Segoe UI", 10),
                     wraplength=330).pack(anchor="w")

            def _drop():
                try:
                    App._toast_stack.remove(win)
                except ValueError:
                    pass
                try:
                    win.destroy()
                except Exception:
                    pass

            for w in (win, outer, inner):
                w.bind("<Button-1>", lambda e: _drop())
            win.update_idletasks()
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            x = sw - win.winfo_width() - 24
            # 21.10: стопка — новые тосты выезжают выше уже открытых
            y = sh - 48 - win.winfo_height()
            for other in list(App._toast_stack):
                try:
                    y = min(y, other.winfo_y() - win.winfo_height() - 8)
                except Exception:
                    pass
            # 24.10: не выпускаем стопку за верх экрана и не копим её
            y = max(8, y)
            while len(App._toast_stack) >= 5:
                old = App._toast_stack.pop(0)
                try:
                    old.destroy()
                except Exception:
                    pass
            App._toast_stack.append(win)
            win.geometry(f"+{x}+{y}")
            win.after(4200, _drop)
        except Exception:
            pass  # тост никогда не мешает работе инструментов

    def begin_run(self):
        """24.10: старт операции — блокировка кнопок и переход в журнал.
        Если уже идёт процесс или фоновая витрина, второй запуск не
        начинается: пишем предупреждение и возвращаем False."""
        if self.runner.running or self._bg_active:
            label = (self.runner._label if self.runner.running
                     else self._bg_label)
            msg = (f"Уже запущено: {label}. Дождитесь окончания "
                   "или нажмите «Стоп».")
            self.log_line(msg + "\n", "warn")
            self.toast(msg, "warn")
            return False
        self._set_busy(True)
        try:
            self._stop_btn.configure(state="normal")
        except Exception:
            pass
        if _cfg_flag("jump_log", True) and self._current_tab != LOG_TAB:
            self._goto_tab(LOG_TAB)
        return True

    def begin_background(self, label):
        """24.10: фоновая задача без subprocess (ё/е-аудит, сбор витрины).
        Ведёт себя как обычный запуск: блокирует кнопки, включает «Стоп»,
        показывает время в статусе."""
        if self.runner.running or self._bg_active:
            msg = (f"Уже запущено: {self._bg_label or self.runner._label}. "
                   "Дождитесь окончания или нажмите «Стоп».")
            self.log_line(msg + "\n", "warn")
            self.toast(msg, "warn")
            return False
        self._bg_active = True
        self._bg_label = label
        self._bg_t0 = time.monotonic()
        self._bg_proc = None
        self._set_busy(True)
        try:
            self._stop_btn.configure(state="normal")
        except Exception:
            pass
        self.status.configure(text=f"выполняется: {label}")
        if _cfg_flag("jump_log", True) and self._current_tab != LOG_TAB:
            self._goto_tab(LOG_TAB)
        self._bg_job = self.after(100, self._bg_pulse)
        return True

    def _bg_pulse(self):
        self._bg_job = None
        if not self._bg_active:
            return
        try:
            s = int(time.monotonic() - self._bg_t0)
            self.status.configure(
                text=f"выполняется: {self._bg_label} • "
                     f"{s // 60}:{s % 60:02d}")
            if self.progress_bar is not None:
                t = (time.monotonic() - self._bg_t0) % 2.4
                tri = t if t <= 1.2 else 2.4 - t
                self.progress_bar.set(0.08 + 0.82 * (tri / 1.2))
                self.progress_label.configure(text="идёт работа…")
        except Exception:
            pass
        self._bg_job = self.after(100, self._bg_pulse)

    def finish_background(self):
        """24.10: завершение фоновой задачи: снять блокировку и пульс."""
        was_stopped = False
        try:
            was_stopped = STOP_FILE.exists()
        except Exception:
            pass
        if self._bg_job:
            try:
                self.after_cancel(self._bg_job)
            except Exception:
                pass
            self._bg_job = None
        self._bg_active = False
        self._bg_proc = None
        self._set_busy(False)
        try:
            self._stop_btn.configure(state="disabled")
        except Exception:
            pass
        try:
            self.progress_bar.set(0)
            self.progress_label.configure(text="")
            self.status.configure(
                text="остановлено" if was_stopped else "готов")
        except Exception:
            pass
        try:
            STOP_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    def stop_all(self):
        """24.10: единая кнопка «Стоп» для Runner и фоновых витрин."""
        if self.runner.running:
            self.runner.stop()
            return
        if not self._bg_active:
            return
        try:
            STOP_FILE.write_text("stop", encoding="utf-8")
        except Exception:
            pass
        proc = self._bg_proc
        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass
        self.log_line("\n[остановка фоновой задачи…]\n")
        self.toast("Останавливаю фоновую задачу", "warn")

    def _set_busy(self, busy):
        """21.10: блокировка кнопок инструментов на время операции.
        «Стоп» и инструменты журнала остаются доступны."""
        state = "disabled" if busy else "normal"
        for b in self._big_buttons:
            try:
                b.configure(state=state)
            except Exception:
                pass

    def _on_close(self):
        """20.10: мягкое закрытие: если процесс пишет файлы — даём ему
        докончить текущий файл (до 15 с), затем закрываем окно.
        24.10: спрашиваем подтверждение, если операция ещё идёт."""
        try:
            if self.runner.running or self._bg_active:
                if _cfg_flag("confirm_close", True):
                    from tkinter import messagebox
                    if not messagebox.askyesno(
                            "Операция выполняется",
                            "Инструмент ещё работает.\n\n"
                            "Остановить его и закрыть окно? Программа "
                            "докончит текущий файл, чтобы не повредить его.",
                            icon="warning", parent=self):
                        return
                self.runner._closing = True
                self.stop_all()
                # 24.10: процесс мог ещё не успеть стартовать — ждём его
                # появления, иначе окно закроется, а процесс останется
                deadline = time.monotonic() + 5
                while (self.runner.proc is None and self.runner.running
                       and time.monotonic() < deadline):
                    time.sleep(0.05)
                p = self.runner.proc
                if p is not None:
                    try:
                        p.wait(timeout=15)
                    except Exception:
                        # 24.10: не оставляем процесс жить после закрытия
                        try:
                            p.kill()
                        except Exception:
                            pass
                # 24.10: фоновая витрина может писать файлы в потоке —
                # даём ей докончить и обработать очередь, чтобы не
                # оборвать запись на середине
                if self._bg_active:
                    deadline = time.monotonic() + 15
                    while self._bg_active and time.monotonic() < deadline:
                        try:
                            self.update()
                        except Exception:
                            break
                        time.sleep(0.05)
        except Exception:
            pass
        try:
            STOP_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        self._save_ui_state()
        self.destroy()

    def _on_done(self, code=0, elapsed=0.0, stopped=False):
        """21.10: завершение операции — разблокировка кнопок, тост и звук.
        Тост завершения и звук разъединены: тост выключается галочкой
        «Тост при завершении», звук — «Звуковые сигналы» (ошибка всегда
        и тостится и звучит, если звук включён).
        24.10: остановка пользователем — отдельное сообщение, не ошибка."""
        self._set_busy(False)
        try:
            self._stop_btn.configure(state="disabled")
        except Exception:
            pass
        label = getattr(self.runner, "_label", "операция")
        mins = f"{int(elapsed) // 60}:{int(elapsed) % 60:02d}"
        if stopped:
            self.status.configure(text="остановлено")
            self.toast(f"Остановлено: {label} ({mins}).\n"
                       "Текущий файл докончен.", "warn")
            return
        # 25.10: для find_cjk код 1 — штатные находки, а не сбой.
        if code == 1 and label == "find_cjk":
            self.status.configure(text="есть замечания")
            _toast_beep("warn")
            if _cfg_flag("toast_done", True):
                self.toast(
                    f"Есть замечания: {label} ({mins}).\n"
                    "Подробности — в журнале.", "warn", beep=False)
            return
        if code == 0:
            self.status.configure(text="готов")
            _toast_beep("ok")  # звук независим от тоста завершения
            if _cfg_flag("toast_done", True):
                self.toast(
                    f"Готово: {label} ({mins}).\nПодробности — в журнале.",
                    "ok", beep=False)
        else:
            self.status.configure(text=f"готов (код {code})")
            self.toast(f"Ошибка: {label} завершился с кодом {code}.\n"
                       "Подробности — в журнале.", "err")

    # --- горячие клавиши ---

    def _bind_hotkeys(self):
        for i, name in enumerate(list(self._tabs), 1):
            if i > 9:
                break
            self.bind_all(f"<Control-Key-{i}>",
                          lambda e, n=name: self._hotkey_tab(n))
        self.bind_all("<Control-s>", lambda e: self._save_cfg_hotkey())
        self.bind_all("<Control-f>", lambda e: self._focus_search())

    def _hotkey_tab(self, name):
        self._goto_tab(name)
        return "break"

    def _focus_search(self):
        self._goto_tab(LOG_TAB)
        self._log_panel.focus_search()
        return "break"

    def _save_cfg_hotkey(self):
        import json
        from gui_config import _load
        try:
            CONFIG_FILE.write_text(
                json.dumps(_load(), ensure_ascii=False, indent=2),
                encoding="utf-8")
            self.log_line("Настройки сохранены.\n", "ok")
            self.toast("Настройки сохранены", "ok", beep=False)
        except Exception as e:
            self.log_line(f"Ошибка сохранения настроек: {e}\n", "err")
        return "break"

    def _save_report(self, text=None):
        if text is None:
            text = self._log_panel.get_text()
        text = (text or "").strip()
        if not text:
            self.toast("Журнал пуст — сохранять нечего", "warn", beep=False)
            return
        base = self._reports_dir()
        pth = filedialog.asksaveasfilename(
            initialdir=str(base), defaultextension=".txt",
            filetypes=[("Текст", "*.txt"), ("Markdown", "*.md")])
        if not pth:
            return
        try:
            Path(pth).write_text(text, encoding="utf-8")
        except Exception as e:
            self.log_line(f"Ошибка сохранения отчёта: {e}\n", "err")
            self.toast("Не удалось сохранить отчёт: проверьте папку",
                       "err")
            return
        self.log_line("Отчёт сохранён: ", "ok")
        self.log_line(f"{pth}\n")
        self.toast(f"Отчёт сохранён: {Path(pth).name}", "ok", beep=False)

    def _reports_dir(self):
        """24.10: папка отчётов из настроек, иначе reports/ рядом."""
        custom = str(CFG.get("report_dir", "") or "").strip()
        if custom:
            custom = os.path.expandvars(os.path.expanduser(custom))
        base = Path(custom) if custom else REPORTS_DIR
        try:
            base.mkdir(parents=True, exist_ok=True)
        except Exception:
            base = REPORTS_DIR
            try:
                base.mkdir(exist_ok=True)
            except Exception:
                pass
        return base


def main():
    sys.excepthook = _sys_excepthook  # 20.10: runtime падения тоже в журнал
    # 26.10 (exe): self-run внутренних инструментов. exe перезапускает
    # себя с "--tool-run <modname> [args...]"; здесь распаковываем и
    # вызываем tools.<modname>.main(args) (find_cjk — отдельный модуль).
    # Никакого GUI: тихий процесс, результат в stdout как обычно.
    if "--tool-run" in sys.argv:
        i = sys.argv.index("--tool-run")
        modname = sys.argv[i + 1] if len(sys.argv) > i + 1 else ""
        args = sys.argv[i + 2:]
        try:
            if modname == "find_cjk":
                import find_cjk
                sys.exit(find_cjk.main(args))
            import importlib
            m = importlib.import_module(f"tools.{modname}")
            sys.exit(m.main(args))
        except SystemExit:
            raise
        except Exception:
            import traceback
            traceback.print_exc()
            try:
                _log_crash(f"tool-run {modname}")
            except Exception:
                pass
            sys.exit(1)
    _log_info(f"START pid={os.getpid()} py={sys.version.split()[0]} "
              f"exe={sys.executable}")
    try:
        app = App()
        _log_info("BUILD DONE")
    except Exception:
        _log_crash("startup")
        raise
    _log_info("MAINLOOP")
    app.mainloop()
    _log_info("CLOSED")


if __name__ == "__main__":
    main()
