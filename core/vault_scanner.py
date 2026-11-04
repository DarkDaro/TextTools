"""
textools core: vault_scanner
Сканирует Obsidian vault, строит граф заметок: файлы, вики-ссылки.
Используется orphan_finder, broken_links, merge_finder.
"""
import re
from pathlib import Path

from core import encoding

SKIP_DIRS = {".obsidian", ".git", "md_replace_backups", ".trash", ".smart-env"}

WIKILINK_RE = re.compile(r"!?\[\[([^\]]+)\]\]")
FENCE_OPEN_RE = re.compile(r"^\s*(```+|~~~+)")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
# markdown-ссылка [текст](цель) и вложение ![альт](цель); цель без скобок
MDLINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s][^)]*)\)")
# внешние адреса и якоря без пути ссылками на заметки не считаются
MD_SKIP_PREFIXES = ("http://", "https://", "ftp://", "ftps://", "mailto:",
                    "data:", "obsidian://", "#", "tel:")


def _clean_link(raw):
    """[[путь/имя#глава|алияс]] -> 'путь/имя' (без .md, главы, алиаса)."""
    raw = raw.strip()
    raw = raw.split("|")[0]      # убрать алиас
    raw = raw.split("#")[0]      # убрать главу
    raw = raw.removesuffix(".md")
    return raw.strip().lower()


def links_from_text(text):
    """04.11: вики-ссылки вне кода — фенсы, инлайн-код и отступные блоки.
    Пример в заметке ([[имя]]) — это пример, а не ссылка: раньше он
    считался битой ссылкой и вешал на заметку ложные связи в графе.
    Отступ в 4+ пробела считается кодом только после пустой строки —
    отступ сразу после элемента списка это продолжение пункта (ссылка
    там настоящая)."""
    links = set()
    in_fence = False
    marker = ""
    in_indented = False
    prev_blank = True
    for line in text.splitlines():
        m = FENCE_OPEN_RE.match(line)
        if m:
            if not in_fence:
                in_fence, marker = True, m.group(1)
            elif m.group(1).startswith(marker):
                in_fence, marker = False, ""
            prev_blank = False
            continue
        if in_fence:
            continue
        if not line.strip():
            prev_blank = True
            continue
        indented = line.startswith("    ")
        if in_indented:
            if indented:
                continue
            in_indented = False
        elif indented and prev_blank:
            in_indented = True
            continue
        prev_blank = False
        for mm in WIKILINK_RE.finditer(INLINE_CODE_RE.sub(" ", line)):
            target = _clean_link(mm.group(1))
            if target:
                links.add(target)
    return links


def _clean_md_target(raw):
    """(цель.md#глава) -> ('путь/цель', 'цель.md#глава'):
    чистая цель для сравнения с индексом (lower, без якоря и .md,
    проценты-эквивы раскрыты) и исходная для показа в отчёте."""
    from urllib.parse import unquote
    raw = raw.strip()
    if raw.startswith("<") and raw.endswith(">"):
        raw = raw[1:-1].strip()
    if not raw or raw.lower().startswith(MD_SKIP_PREFIXES):
        return None
    target = unquote(raw).strip()
    target = target.split("#", 1)[0].strip()  # якорь внутри файла
    if not target:
        return None
    low = target.replace("\\", "/").lower()
    if low.endswith(".md"):
        low = low[:-3]
    return low, target


def md_links_from_text(text):
    """Markdown-ссылки [текст](цель) вне кода — те же фенсы, инлайн-код
    и отступные блоки, что у вики-ссылок. Возвращает set пар
    (чистая_цель, исходная_цель). Внешние адреса (http, mailto и т.п.)
    и чистые якоря пропускаются; изображения ![]() считаются ссылками
    на вложения — тоже проверяются."""
    out = set()
    in_fence = False
    marker = ""
    in_indented = False
    prev_blank = True
    for line in text.splitlines():
        m = FENCE_OPEN_RE.match(line)
        if m:
            if not in_fence:
                in_fence, marker = True, m.group(1)
            elif m.group(1).startswith(marker):
                in_fence, marker = False, ""
            prev_blank = False
            continue
        if in_fence:
            continue
        if not line.strip():
            prev_blank = True
            continue
        indented = line.startswith("    ")
        if in_indented:
            if indented:
                continue
            in_indented = False
        elif indented and prev_blank:
            in_indented = True
            continue
        prev_blank = False
        for mm in MDLINK_RE.finditer(INLINE_CODE_RE.sub(" ", line)):
            pair = _clean_md_target(mm.group(1))
            if pair:
                out.add(pair)
    return out


class Note:
    __slots__ = ("path", "rel", "stem", "links", "md_links", "hash")

    def __init__(self, path, rel, links, hash_, md_links=None):
        self.path = path      # Path абсолютный
        self.rel = rel        # относительный путь (str, осн. регистр)
        self.stem = path.stem.lower()   # имя файла без .md, lower
        self.links = links    # set чистых вики-ссылок (lower)
        self.md_links = md_links or set()  # set пар (чистая, исходная)
        self.hash = hash_     # md5 контента (hex) или None

    @property
    def name(self):
        return self.rel


def scan_vault(vault, exts=(".md",), limit=None):
    """
    Сканирует vault, возвращает (notes, basenames, relpaths, attachments):
      notes: list[Note]
      basenames: set имён .md-файлов без .md (lower) — существующие цели
      relpaths: set относительных путей без .md (lower)
      attachments: set имён и rel-путей прочих файлов (вложения, .canvas,
        lower, с расширением) — цели ![[…]] и [[x.png]] для broken_links.
        Собирается в том же проходе; при --limit — до лимита.
    """
    vault = Path(vault)
    basenames = set()
    relpaths = set()
    attachments = set()
    md_files = []
    count = 0
    # 18.09: один файл как вход — иначе rglob по файлу даёт пустоту
    if vault.is_file():
        candidates = [(vault, vault.name)]
    else:
        candidates = [(f, f.relative_to(vault)) for f in sorted(vault.rglob("*"))]
    for f, rel in candidates:
        if not f.is_file() or f.suffix.lower() != ".md":
            # 04.11: не-markdown файлы — вложения; индекс имён нужен,
            # иначе все ![[картинка.png]] попадают в битые ссылки
            if f.is_file() and f.suffix.lower() != ".md" \
                    and not (set(f.parts) & SKIP_DIRS):
                attachments.add(f.name.lower())
                attachments.add(
                    str(rel).replace("\\", "/").lower())
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
        # 20.10: cp1251/koi8 заметки больше не выпадают из графа — читаем
        # через read_any (utf-8 / autodetect)
        text, _enc = encoding.read_any(f)
        if text is None:
            notes.append(Note(f, str(rel), set(), None))
            continue
        links = links_from_text(text)
        md_links = md_links_from_text(text)
        hash_ = None
        try:
            # 26.10: локальный import hashlib был мёртвым (хеш берёт hashlib_md5 ниже) — отключён
            # import hashlib
            norm = "\n".join(text.split())  # без различий пробелов
            hash_ = hashlib_md5(norm)
        except Exception:
            pass
        notes.append(Note(f, str(rel), links, hash_, md_links))
    return notes, basenames, relpaths, attachments


def hashlib_md5(text):
    import hashlib
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def is_resolved(target, basenames, relpaths, attachments=frozenset()):
    """Ссылка считается рабочей, если цель существует по пути или по имени.
    attachments — имена/пути прочих файлов (вложения): 04.11 ссылки
    ![[файл.png]] и [[x.canvas]] больше не считаются битыми."""
    if target in relpaths or target in attachments:
        return True
    base = target.rsplit("/", 1)[-1]
    return base in basenames or base in attachments


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
