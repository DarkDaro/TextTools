# -*- coding: utf-8 -*-
"""
core: encoding — определение кодировки текстовых файлов (01.10).

Раньше всё читалось только как UTF-8: koi8/cp1251 файлы молча выпадали
из всех проверок. Теперь read_any() подбирает кодировку (charset-normalizer,
если есть, иначе цепочка типовых для этого проекта).
"""
from pathlib import Path

FALLBACK_ENCODINGS = ("utf-8-sig", "cp1251", "koi8-r", "cp866", "cp1252")


def detect(data):
    """Кодировка байтов или None. data: bytes."""
    if not data:
        return "utf-8"
    # 01.10: однобайтовая кириллица детерминированно: в koi8-r строчные
    # русские буквы лежат в 0xC0-0xDF, в cp1251 — в 0xE0-0xFF. Правильная
    # декодировка даёт текст с преобладанием строчных. charset-normalizer
    # на коротких текстах ошибается (называет shift_jis), поэтому решаем сами
    cyr_lo = sum(1 for b in data if 0xC0 <= b <= 0xDF)  # строчные у koi8
    cyr_up = sum(1 for b in data if 0xE0 <= b <= 0xFE)  # строчные у cp1251
    if cyr_lo + cyr_up > len(data) * 0.2:
        return "koi8-r" if cyr_lo >= cyr_up else "cp1251"
    try:
        from charset_normalizer import from_bytes
        best = from_bytes(data).best()
        if best is not None:
            return best.encoding
    except Exception:
        pass
    for en in FALLBACK_ENCODINGS:
        try:
            data.decode(en)
            return en
        except (UnicodeDecodeError, LookupError):
            continue
    return None


def read_any(path):
    """(текст, кодировка). Текст None, если файл вовсе не текст."""
    path = Path(path)
    try:
        data = path.read_bytes()
    except (PermissionError, OSError):
        return None, None
    if not data:
        return "", "utf-8"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        return data.decode("utf-8-sig"), "utf-8-sig"
    except UnicodeDecodeError:
        pass
    enc = detect(data)
    if enc is None:
        return None, None
    try:
        return data.decode(enc), enc
    except (UnicodeDecodeError, LookupError):
        return None, None


def is_utf8(path):
    """True, если файл уже валидный UTF-8 (включая пустой)."""
    try:
        data = Path(path).read_bytes()
    except (PermissionError, OSError):
        return True  # не наше дело — пропускаем молча
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False
