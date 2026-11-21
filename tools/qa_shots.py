#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qa_shots — скриншот-автоматика визуального приёка GUI (TD-02).

Сам открывает окно приложения, проходит по вкладкам в заданных темах
и масштабах, снимает каждую вкладку в PNG и печатает чек-лист для
просмотра человеком. Снимки складываются в reports/screenshots/ —
папка в git не входит, в репозиторий попадает только этот скрипт.

Что проверяется автоматически (плоский дизайн → мало цветов):
уникальные цвета кадра; по-настоящему пустой кадр — до 10, рабочий —
десятки. Подозрительные кадры помечаются в чек-листе «ПУСТО?», но
финальное решение — за человеком: скрипт не видит обрезанные подсказки
и кривые паддинги, он только готовит материал.

Запуск:
    python tools/qa_shots.py                     # темы × масштабы × вкладки
    python tools/qa_shots.py --themes dark       # только тёмная
    python tools/qa_shots.py --scales 1.0        # без 1.25
    python tools/qa_shots.py --size 980x640      # узкое окно
    python tools/qa_shots.py --tabs vault,settings
    python tools/qa_shots.py --fonts "DejaVu Sans,DejaVu Sans Mono"

Нужен дисплей (на Linux — Xvfb) и Pillow (только для снимка):
    pip install pillow

Конфиг gui_config.json на время съёмки подменяется и восстанавливается;
окно по очереди переключает вкладки, ничего не запускает и не пишет.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_FILE = PROJECT_ROOT / "gui_config.json"
BACKUP = Path("/tmp/gui_config.json.qa_shots.bak")

# имя вкладки -> латинский слаг для имени файла
SLUGS = {
    "Писателям": "writers",
    "Имена персонажей": "names",
    "Хранилище": "vault",
    "Чистка": "clean",
    "Замены": "replace",
    "Помодоро": "pomodoro",
    "Настройки": "settings",
    "Журнал": "log",
}

# демо-строки журнала, чтобы вкладка «Журнал» не была пустой
LOG_DEMO = [
    "14:22:05  utf8: проверка кодировок — 60 файлов, всё в UTF-8\n",
    "14:22:07  obsidian-check: 2 замечания (WARN), отчёт reports/obsidian-check.md\n",
    "14:22:09  consistency: расхождений имён не найдено (реестр: 24 персонажа)\n",
    "14:22:12  phrase-check: 17 вхождений штампов в 9 файлах — витрина открыта\n",
    "14:22:15  готово: 1 мин 12 с\n",
]


def _load_gui():
    """gui_ctk — .pyw-файл, грузим как в test_settings.py."""
    from importlib.machinery import SourceFileLoader
    import importlib.util
    loader = SourceFileLoader("gui_ctk", str(PROJECT_ROOT / "gui_ctk.pyw"))
    spec = importlib.util.spec_from_loader("gui_ctk", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gui_ctk"] = mod
    loader.exec_module(mod)
    return mod


def _pump(app, seconds=0.5):
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.02)


def _patch_config(fonts=None):
    """Бэкап конфига + запись шрифтовых переопределений (для Xvfb)."""
    shutil.copy2(CONFIG_FILE, BACKUP)
    try:
        cfg = (json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
               if CONFIG_FILE.is_file() else {})
    except Exception:
        cfg = {}
    if fonts:
        fam, _, mono = fonts.partition(",")
        cfg["ui.font_family"] = fam.strip()
        cfg["ui.mono_family"] = (mono or fam).strip() or fam.strip()
    cfg["remember_geometry"] = False
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                           encoding="utf-8")


def _restore_config():
    if BACKUP.is_file():
        shutil.copy2(BACKUP, CONFIG_FILE)


def run_session(themes, scales, size, tabs, fonts, out_dir, xdisplay):
    """Съёмка: процесс с GUI. Печатает строки SHOT <json> — их собирает
    родитель (или человек при прямом запуске)."""
    from PIL import ImageGrab
    from collections import Counter

    import customtkinter as ctk
    gui = _load_gui()

    w, h = size
    out_dir.mkdir(parents=True, exist_ok=True)
    shots = []

    _patch_config(fonts)
    try:
        app = None
        for scale in scales:
            if app is not None:
                app.destroy()
                app = None
                time.sleep(0.3)
            # масштаб применяется при построении виджетов
            ctk.set_widget_scaling(float(scale))
            app = gui.App()
            app.geometry(f"{w}x{h}+40+30")
            _pump(app, 1.5)
            try:
                for line in LOG_DEMO:
                    app.log_line(line)
            except Exception as e:
                print(f"demo log skipped: {e}", file=sys.stderr)
            names = list(app.nb._tab_dict.keys())
            for theme in themes:
                app._on_theme_change(theme)
                _pump(app, 1.0)
                for i, name in enumerate(names):
                    slug = SLUGS.get(name, f"tab{i}")
                    if tabs and slug not in tabs:
                        continue
                    app._goto_tab(name, save=False)
                    _pump(app, 0.8)
                    app.update_idletasks()
                    x, y = app.winfo_rootx(), app.winfo_rooty()
                    bbox = (x, y, x + w, y + h)
                    img = ImageGrab.grab(bbox=bbox, xdisplay=xdisplay)
                    uniq = len(Counter(img.convert("RGB").getdata()))
                    path = out_dir / f"{slug}-s{scale}-{theme}-{w}x{h}.png"
                    img.save(path, optimize=True)
                    rec = {"file": str(path.relative_to(PROJECT_ROOT)),
                           "kb": path.stat().st_size // 1024,
                           "colors": uniq, "tab": name,
                           "theme": theme, "scale": scale}
                    shots.append(rec)
                    flag = "  ПУСТО?" if uniq < 15 else ""
                    print("SHOT " + json.dumps(rec, ensure_ascii=False))
                    print(f"  {path.name}: {img.size[0]}x{img.size[1]}, "
                          f"{rec['kb']} KB, цветов {uniq}{flag}")
        if app is not None:
            app.destroy()
    finally:
        _restore_config()
    print(f"ГОТОВО: {len(shots)} снимков в {out_dir}")
    return 0


def main(opts=None):
    ap = argparse.ArgumentParser(
        description="скриншот-автоматика визуального приёка GUI (TD-02): "
                    "вкладки × темы × масштабы в reports/screenshots/")
    ap.add_argument("--out", default="reports/screenshots",
                    help="куда класть PNG (по умолчанию reports/screenshots, "
                         "в git не входит)")
    ap.add_argument("--themes", default="light,dark",
                    help="темы через запятую: light, dark")
    ap.add_argument("--scales", default="1.0,1.25",
                    help="масштабы через запятую: 1.0, 1.25")
    ap.add_argument("--size", default="1280x800",
                    help="размер окна: ШИРИНАxВЫСОТА (1280x800 или 980x640)")
    ap.add_argument("--tabs", default="",
                    help="слаги вкладок через запятую "
                         "(writers,names,vault,clean,replace,pomodoro,"
                         "settings,log); пусто — все")
    ap.add_argument("--fonts", default="",
                    help='переопределить шрифты: "Segoe UI,Consolas" '
                         "(нужно в Xvfb, где нет фирменных шрифтов)")
    args = ap.parse_args(opts if opts is not None else sys.argv[1:])

    try:
        import PIL  # noqa: F401
    except ImportError:
        print("Нужен Pillow: pip install pillow", file=sys.stderr)
        return 2

    themes = [t.strip() for t in args.themes.split(",") if t.strip()]
    scales = []
    for raw in args.scales.split(","):
        v = float(raw.strip().replace(",", "."))
        if not 0.5 <= v <= 2.0:
            print(f"масштаб {v} вне 0.5–2.0", file=sys.stderr)
            return 2
        scales.append(v)
    try:
        w_s, _, h_s = args.size.lower().partition("x")
        size = (int(w_s), int(h_s))
    except ValueError:
        print(f"--size: ожидается ШИРИНАxВЫСОТА, получено {args.size!r}",
              file=sys.stderr)
        return 2
    tabs = {t.strip() for t in args.tabs.split(",") if t.strip()}
    out_dir = (PROJECT_ROOT / args.out) if not Path(args.out).is_absolute() \
        else Path(args.out)

    if os.environ.get("QA_SHOTS_WORKER") == "1":
        return run_session(themes, scales, size, tabs, args.fonts,
                           out_dir, os.environ.get("QA_SHOTS_DISPLAY"))

    # родитель: каждый масштаб — свежий процесс (масштаб применяется
    # при построении виджетов; так же его видит обычный запуск)
    env = dict(os.environ, QA_SHOTS_WORKER="1")
    failed = False
    for scale in scales:
        env["QA_SHOTS_DISPLAY"] = os.environ.get("DISPLAY", "")
        r = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()),
             "--themes", ",".join(themes),
             "--scales", str(scale),
             "--size", args.size,
             *(["--tabs", ",".join(sorted(tabs))] if tabs else []),
             *(["--fonts", args.fonts] if args.fonts else []),
             "--out", str(out_dir)],
            env=env, cwd=str(PROJECT_ROOT))
        if r.returncode != 0:
            failed = True
    # чек-лист для человека
    shots = sorted(out_dir.glob("*.png"))
    print("\nЧек-лист приёмки (смотреть глазами):")
    for p in shots:
        print(f"  - {p.name}")
    print(f"Всего файлов: {len(shots)}. Подсказки, паддинги и обрезы "
          "скрипт не видит — просматривает человек.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
