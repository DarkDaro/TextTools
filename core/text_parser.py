"""
textools core: text_parser
Чтение .md/.txt/.docx (22.09: добавлен docx через core.docx_io),
токенизация, поиск кандидатов-имён.
"""
import re
from pathlib import Path

# 22.09: docx — бинарный zip, читается через docx_io
TEXT_EXTS = (".md", ".txt", ".docx")

# Слова, которые часто встречаются с заглавной буквы, но не имена
# (начало диалога, обращения, месяцы, и т.д.)
STOPLIST = {
    # местоимения / частые слова в начале реплик
    "я", "он", "она", "оно", "они", "мы", "вы", "ты", "это", "этот", "эта",
    "как", "так", "что", "чтобы", "кто", "все", "всё", "весь", "вся",
    "но", "ну", "да", "нет", "не", "ни", "уже", "ещё", "еще", "только",
    "там", "тут", "здесь", "теперь", "потом", "тогда", "когда", "если",
    "может", "можно", "нужно", "надо", "хочу", "буду", "будет", "быть",
    # обращения и титулы-слова (сами по себе не имя)
    "господин", "госпожа", "товарищ", "сэр", "мастер", "учитель",
    "наставник", "старейшина", "капитан", "командир", "принц", "принцесса",
    "король", "королева", "император", "лорд", "леди", "барон",
    # месяцы / дни
    "январь", "февраль", "март", "апрель", "май", "июнь", "июль",
    "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
    "понедельник", "вторник", "среда", "четверг", "пятница", "суббота",
    # служебное
    "прим", "внимание", "итог", "итоги", "заметка", "главное", "вопрос",
    "ответ", "пример", "часть", "глава", "раздел", "день", "ночь", "утро",
    "вечер", "год", "месяц", "неделя",
}

WORD_RE = re.compile(r"[А-ЯЁа-яёA-Za-z][А-ЯЁа-яёA-Za-z-]+")
SENT_SPLIT_RE = re.compile(r"[.!?…]+\s|[.!?…]+$")


def norm_yo(s):
    """01.10: ё -> е — одинаковая длина, индексы не съезжают.
    «Елена» и «Елёна», «все чаще» и «всё чаще» перестают быть разными словами."""
    return s.replace("ё", "е").replace("Ё", "Е")

# 01.10: мягкая остановка — GUI кладёт файл-флаг, инструменты проверяют
# между файлами и завершаются сами (жёсткий kill рискует побить docx)
STOP_FILE = Path(__file__).resolve().parent.parent / "stop.flag"


def stop_requested():
    try:
        return STOP_FILE.exists()
    except OSError:
        return False


def read_text(path):
    """Читает файл как UTF-8; при неудаче — определяет кодировку
    (core.encoding, 01.10: koi8/cp1251 больше не выпадают из проверок).
    .docx — через docx_io. Возвращает None, если не читается."""
    path = Path(path)
    if path.suffix.lower() == ".docx":
        try:
            from core import docx_io
            return docx_io.read_text(path)
        except ImportError:
            pass
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError, OSError):
        pass
    try:
        from core import encoding
        text, _enc = encoding.read_any(path)
        return text
    except Exception:
        return None


def iter_text_files(root, exts=TEXT_EXTS, limit=None):
    """Итерация по файлам текстов. По умолчанию .md/.txt/.docx (22.09).
    Пропускает служебные папки."""
    # 22.09: guard ДО Path() — Path('') становится '.', пустоту не ловит
    if not root or not str(root).strip():
        raise ValueError("Путь не указан (пустой --input)")
    root = Path(root)
    if not root.exists():
        raise ValueError(f"Путь не найден: {root}")
    if root.is_file():
        yield root
        return
    files = sorted(root.rglob("*"))
    count = 0
    for f in files:
        if stop_requested():  # 01.10: мягкая остановка
            return
        if not f.is_file() or f.suffix.lower() not in exts:
            continue
        parts = set(f.parts)
        if parts & {".obsidian", ".git", "md_replace_backups"}:
            continue
        yield f
        count += 1
        if limit and count >= limit:
            return


def sentences(text):
    """Разбивает текст на предложения."""
    return [s.strip() for s in SENT_SPLIT_RE.split(text) if s.strip()]


def find_name_candidates(text, known=None, min_len=3):
    """
    Ищет слова с заглавной буквы в середине предложения.
    known: set слов, которые уже известны (не включать в кандидаты).
    Возвращает список (слово_в_начальной_форме_приблизительно, слово).
    """
    known = known or set()
    # 01.10: ё/е — одна буква для сравнения («Елена» = «Елёна»)
    known = {norm_yo(k) for k in known}
    results = []
    for sent in sentences(text):
        words = WORD_RE.findall(sent)
        for idx, w in enumerate(words):
            if idx == 0:
                continue  # первое слово предложения пропускаем
            # слово с заглавной, не полностью из заглавных (аббревиатуры)
            if w[0].isupper() and not w.isupper() and len(w) >= min_len:
                low = norm_yo(w.lower())
                if low in STOPLIST or low in known:
                    continue
                results.append(low)
    return results


def find_bigrams(text, known=None, min_len=3):
    """Пары подряд идущих заглавных слов (Имя Фамилия, Мастер Кайдзо)."""
    known = known or set()
    known = {norm_yo(k) for k in known}  # 01.10: ё/е
    results = []
    for sent in sentences(text):
        words = WORD_RE.findall(sent)
        for idx in range(len(words) - 1):
            a, b = words[idx], words[idx + 1]
            if (a[:1].isupper() and b[:1].isupper()
                    and len(a) >= min_len and len(b) >= min_len):
                la, lb = norm_yo(a.lower()), norm_yo(b.lower())
                if la in STOPLIST or lb in STOPLIST:
                    continue
                if la in known or lb in known:
                    continue
                results.append(f"{la} {lb}")
    return results