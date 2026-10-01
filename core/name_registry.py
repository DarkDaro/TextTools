"""
textools core: name_registry
Реестр имён в формате characters.yaml (совместим с md-replace):

- имя: Эрика
  формы: [Эрика, Эрики, ...]
  старое: [Лика, ...]
  старое_опасное: []
  опечатки: []
"""
import yaml
from pathlib import Path

FIELDS = ("имя", "формы", "старое", "старое_опасное", "опечатки")


def load_registry(path):
    """Загружает реестр. Возвращает список словарей."""
    p = Path(path)
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data:
        return []
    # нормализация полей
    chars = []
    for c in data:
        ch = {"имя": c.get("имя", "").strip()}
        for fld in FIELDS[1:]:
            ch[fld] = list(c.get(fld) or [])
        chars.append(ch)
    return [c for c in chars if c["имя"]]


def save_registry(path, chars):
    """Сохраняет реестр (UTF-8, читаемый вид)."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(chars, f, allow_unicode=True, sort_keys=False,
                       default_flow_style=None, width=100)


def known_forms(chars):
    """Все известные формы (текущие + старые + опечатки), в нижнем регистре."""
    s = set()
    for c in chars:
        for fld in FIELDS[1:]:
            for w in c[fld]:
                s.add(w.lower())
        s.add(c["имя"].lower())
    return s


def known_first_names(chars):
    """Первые слова составных имён (Мастер -> титул), чтобы bigram-поиск
    не предлагал 'Мастер Х' как нового персонажа."""
    s = set()
    for c in chars:
        first = c["имя"].split()[0] if " " in c.get("имя", "") else None
        if first:
            s.add(first.lower())
        for fld in FIELDS[1:]:
            for w in c[fld]:
                if " " in w:
                    s.add(w.split()[0].lower())
    return s