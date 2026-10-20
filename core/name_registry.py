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
    """Загружает реестр. Возвращает список словарей.
    20.10: битый/чужой YAML не роняет инструмент — понятное сообщение
    и пустой реестр (старое поведение сохранено для отсутствующего файла)."""
    p = Path(path)
    if not p.exists():
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Реестр не прочитан: {p.name}: {e}")
        return []
    if not data:
        return []
    if not isinstance(data, list) or not all(
            isinstance(c, dict) for c in data):
        print(f"Ожидался список персонажей в {p.name} — реестр не загружен.")
        return []
    # нормализация полей
    chars = []
    for c in data:
        ch = {"имя": str(c.get("имя", "")).strip()}
        for fld in FIELDS[1:]:
            v = c.get(fld)
            ch[fld] = (v if isinstance(v, list) else ([v] if v else []))
        chars.append(ch)
    return [c for c in chars if c["имя"]]


def save_registry(path, chars):
    """Сохраняет реестр (UTF-8, читаемый вид). 20.10: атомарно — через
    временный файл и os.replace, сбой посреди записи не теряет реестр."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(chars, f, allow_unicode=True, sort_keys=False,
                       default_flow_style=None, width=100)
    import os
    os.replace(tmp, path)


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