"""
textools core: vault_scanner
Сканирует Obsidian vault, строит граф заметок: файлы, вики-ссылки.
Используется orphan_finder, broken_links, merge_finder.
"""
import re
from pathlib import Path

SKIP_DIRS = {".obsidian", ".git", "md_replace_backups", ".trash", ".smart-env"}

WIKILINK_RE = re.compile(r"!?\[\[([^\]]+)\]\]")


def _clean_link(raw):
    """[[путь/имя#глава|алияс]] -> 'путь/имя' (без .md, главы, алиаса)."""
    raw = raw.strip()
    raw = raw.split("|")[0]      # убрать алиас
    raw = raw.split("#")[0]      # убрать главу
    raw = raw.removesuffix(".md")
    return raw.strip().lower()


class Note:
    __slots__ = ("path", "rel", "stem", "links", "hash")

    def __init__(self, path, rel, links, hash_):
        self.path = path      # Path абсолютный
        self.rel = rel        # относительный путь (str, осн. регистр)
        self.stem = path.stem.lower()   # имя файла без .md, lower
        self.links = links    # set чистых ссылок (lower)
        self.hash = hash_     # md5 контента (hex) или None

    @property
    def name(self):
        return self.rel


def scan_vault(vault, exts=(".md",), limit=None):
    """
    Сканирует vault, возвращает (notes, basenames, relpaths):
      notes: list[Note]
      basenames: set имён файлов без .md (lower) — существующие цели
      relpaths: set относительных путей без .md (lower)
    """
    vault = Path(vault)
    basenames = set()
    relpaths = set()
    md_files = []
    count = 0
    # 18.09: один файл как вход — иначе rglob по файлу даёт пустоту
    if vault.is_file():
        candidates = [(vault, vault.name)]
    else:
        candidates = [(f, f.relative_to(vault)) for f in sorted(vault.rglob("*"))]
    for f, rel in candidates:
        if not f.is_file() or f.suffix.lower() != ".md":
            continue
        if set(f.parts) & SKIP_DIRS:
            continue
        basenames.add(f.stem.lower())
        # 01.10: нормализуем \ в / — вики-ссылки всегда с /, на Windows
        # Path даёт \ и ссылка на вложенную заметку по пути не матчится
        relpaths.add(str(rel).removesuffix(".md").replace("\\", "/").lower())
        md_files.append((f, rel))
        count += 1
        if limit and count >= limit:
            break

    notes = []
    for f, rel in md_files:
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError, OSError):
            notes.append(Note(f, str(rel), set(), None))
            continue
        links = set()
        for m in WIKILINK_RE.finditer(text):
            target = _clean_link(m.group(1))
            if target:
                links.add(target)
        hash_ = None
        try:
            import hashlib
            norm = "\n".join(text.split())  # без различий пробелов
            hash_ = hashlib_md5(norm)
        except Exception:
            pass
        notes.append(Note(f, str(rel), links, hash_))
    return notes, basenames, relpaths


def hashlib_md5(text):
    import hashlib
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def is_resolved(target, basenames, relpaths):
    """Ссылка считается рабочей, если цель существует по пути или по имени."""
    if target in relpaths:
        return True
    base = target.rsplit("/", 1)[-1]
    return base in basenames


def incoming_filter(notes, target_note, basenames, relpaths):
    """True, если на заметку кто-то ссылается."""
    t_rel = str(target_note.rel).removesuffix(".md").lower()
    stems = {target_note.stem}
    for n in notes:
        if n is target_note:
            continue
        for lnk in n.links:
            if lnk == t_rel or lnk.rsplit("/", 1)[-1] in stems:
                return True
    return False