# -*- coding: utf-8 -*-
"""
core: fuse — предохранители от зависаний (21.11, просьба владельца
«поработай над оптимизацией тяжёлых скриптов и зависаний, добавь
предохранители»).

Зависания бывали на больших хранилищах: обход читает каждую заметку
целиком, и один гигантский файл или бесконечный по времени скан
выглядели как «программа зависла». Предохранитель — это заранее
выставленный предел, при котором операция сама останавливается и
соизмеримо отчёту объясняет, что и почему не дочитала.

Три предохранителя:
  1. размер файла: заметки крупнее N МБ пропускаются с записью в
     сводку (текст целиком в память всё равно не лезет нормально);
  2. бюджет времени: после N минут обход прекращается между файлами —
     та же семантика, что у кнопки «Стоп», только срабатывает сама;
  3. стоп-файл (уже был): stop.flag от кнопки «Стоп» проверяется
     здесь же, чтобы весь обход останавливался единообразно.

Цепочка источников, первый выигрывает:
  1. явный аргумент (--max-mb / --max-min; 0 = выключить);
  2. ключ gui_config.json (fuse.max_mb / fuse.max_min);
  3. встроенная константа (64 МБ / 20 минут).

Конфиг читается напрямую и только на чтение — так же, как язык в
core/lang.py: любая беда деградирует во встроенную константу.
"""
import json
import time
from pathlib import Path

from core.text_parser import STOP_FILE, stop_requested

# встроенные константы; 0 при чтении конфига = предохранитель выключен
DEFAULT_MAX_MB = 64
DEFAULT_MAX_MIN = 20

MB = 1024 * 1024


def _from_config(key):
    """Число из gui_config.json или None (нет файла, битый JSON, не число)."""
    try:
        from gui_config import CONFIG_FILE
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        v = data.get(key)
        if isinstance(v, (int, float)) and v >= 0:
            return float(v)
    except Exception:
        pass
    return None


def _pick(explicit, key, default):
    """explicit (0 = выключено) > конфиг > встроенная константа."""
    if explicit is not None:
        try:
            return max(0.0, float(explicit))
        except (TypeError, ValueError):
            return float(default)
    cfg = _from_config(key)
    if cfg is not None:
        return cfg
    return float(default)


class Fuse:
    """Пределы одной операции. Проверяется между файлами — сама
    проверка дешевле микросекунды и на зависания влиять не может."""

    def __init__(self, max_mb=None, max_min=None, log=print,
                 stop_file=None):
        mb = _pick(max_mb, "fuse.max_mb", DEFAULT_MAX_MB)
        mn = _pick(max_min, "fuse.max_min", DEFAULT_MAX_MIN)
        self.max_mb = mb
        self.max_bytes = int(mb * MB) if mb > 0 else 0
        self.deadline = time.monotonic() + mn * 60 if mn > 0 else None
        self.max_min = mn
        self.log = log
        self.stop_file = Path(stop_file) if stop_file else STOP_FILE
        self.skipped = []      # [(путь, причина)]
        self.stopped_by = ""   # почему остановились раньше времени

    # --- проверки ------------------------------------------------------

    def check(self):
        """True — можно продолжать. Стоп-файл и дедлайн."""
        try:
            if self.stop_file.exists() or stop_requested():
                self.stopped_by = "стоп-файл (кнопка «Стоп»)"
                return False
        except OSError:
            pass
        if self.deadline is not None and time.monotonic() > self.deadline:
            self.stopped_by = f"лимит времени ({self.max_min:g} мин)"
            return False
        return True

    def allow_file(self, path):
        """True — файл можно читать. Слишком крупный пропускает и
        запоминает; заодно проверяет стоп/дедлайн."""
        if not self.check():
            return False
        if self.max_bytes:
            try:
                size = Path(path).stat().st_size
            except OSError:
                return True
            if size > self.max_bytes:
                if size < MB:  # мелкие — в КБ, чтобы не было «0.0 МБ»
                    why = f"{size / 1024:.0f} КБ > {self.max_mb:g} МБ"
                else:
                    why = f"{size / MB:.1f} МБ > {self.max_mb:g} МБ"
                self.skipped.append((str(path), why))
                return False
        return True

    # --- отчёт ---------------------------------------------------------

    def summary(self):
        """Строки о сработавших предохранителях ([] — всё дочитано)."""
        rows = []
        for path, why in self.skipped:
            rows.append(f"Предохранитель: пропущен {path} — {why}")
        if self.stopped_by:
            rows.append(f"Предохранитель: остановка — {self.stopped_by}")
        return rows

    def report(self):
        """Напечатать сводку, если предохранители сработали."""
        rows = self.summary()
        if rows:
            for r in rows:
                self.log(r)
        return rows


def add_args(ap):
    """Общие флаги предохранителей для тяжёлых команд."""
    g = ap.add_argument_group("предохранители")
    g.add_argument("--max-mb", type=float, default=None,
                   help="пропускать файлы крупнее N МБ (0 — выключить; "
                        "по умолчанию из настроек, иначе 64)")
    g.add_argument("--max-min", type=float, default=None,
                   help="остановиться через N минут обхода (0 — "
                        "выключить; по умолчанию из настроек, иначе 20)")
    return ap


def from_args(args, log=print):
    """Fuse по флагам команды (--max-mb/--max-min)."""
    return Fuse(max_mb=getattr(args, "max_mb", None),
                max_min=getattr(args, "max_min", None), log=log)
