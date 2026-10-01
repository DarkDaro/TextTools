"""Обёртка конфига для виджетов (get/set с автосохранением)."""
from pathlib import Path
import json

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
            CONFIG_FILE.write_text(
                json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass


CFG = Cfg()