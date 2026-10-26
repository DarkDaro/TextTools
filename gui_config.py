"""Обёртка конфига для виджетов (get/set с автосохранением)."""
import sys
from pathlib import Path
import json
import os

# 26.10: exe (PyInstaller one-file): конфиг рядом с exe, не во
# временном _MEIPASS — иначе настройки молча теряются при перезапусках.
if getattr(sys, "frozen", False):
    CONFIG_FILE = Path(sys.executable).parent / "gui_config.json"
else:
    CONFIG_FILE = Path(__file__).parent / "gui_config.json"

_config = None


def _load():
    global _config
    if _config is None:
        if CONFIG_FILE.exists():
            try:
                _config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                _config = {}
        else:
            _config = {}
    return _config


def reset():
    """20.10: очистить конфиг в памяти (файл уже удалён снаружи) — иначе
    самое следующее Cfg.set молча восстановит старые настройки."""
    global _config
    _config = {}


class Cfg:
    """Доступ к конфигу: get/set, автосохранение при каждом set."""

    def __init__(self):
        self.home = Path.home()

    def get(self, key, default=""):
        # 18.09: default_vault подставляется в пустые vault-поля
        v = _load().get(key, default)
        if not v and key.endswith("_input") and key != "default_vault":
            v = _load().get("default_vault", "")
        return v

    def set(self, key, value):
        cfg = _load()
        cfg[key] = value
        try:
            # 20.10: атомарная запись — сбой посреди не оставит битый JSON
            tmp = Path(str(CONFIG_FILE) + ".tmp")
            tmp.write_text(
                json.dumps(cfg, ensure_ascii=False, indent=2),
                encoding="utf-8")
            os.replace(tmp, CONFIG_FILE)
        except Exception:
            try:
                Path(str(CONFIG_FILE) + ".tmp").unlink(missing_ok=True)
            except Exception:
                pass


CFG = Cfg()
