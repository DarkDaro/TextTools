# -*- coding: utf-8 -*-
"""
clean_text_files.py — чистка txt/docx/md от китайских символов и мусора от ИИ.

Использование:
    python clean_text_files.py <путь>            # только отчёт
    python clean_text_files.py <путь> --fix      # чистить (с .bak бэкапами)

<путь> — файл или папка (папка обходится рекурсивно).

Что удаляется: всё, что не входит в разрешённый набор:
  - ASCII печатные (буквы, цифры, пунктуация, пробелы)
  - Кириллица (вкл. Ё, украинские ґєії)
  - Типографика: — – « » „ " " ' ' … № ° ± × ÷ § © ® ™
  - \\n, \\r, \\t
Что НЕ трогается: .bak файлы, сам скрипт, docx-служебные части (стили и т.п. не читаем).
"""

import sys
import os
import re
import shutil
import zipfile
import unicodedata
from collections import Counter

ALLOWED_EXPLICIT = set("—–«»„“”‘’…№°±×÷§©®™")
ALLOWED_RANGES = [
    (0x0020, 0x007E),   # ASCII printable
    (0x0400, 0x04FF),   # Cyrillic + Cyrillic Supplement
    (0x2010, 0x2015),   # dashes
    (0x2018, 0x201F),   # quotes
    (0x2026, 0x2026),   # ellipsis
    (0x2116, 0x2116),   # numero
]

# 22.09: маппинг «мусор → осмысленный эквивалент» вместо удаления
# (синтетика: fullwidth знаки препинания удалялись и склеивали слова)
CHAR_MAP = {
    0xFF0C: ",",   # ， fullwidth comma
    0xFF01: "!",   # ！ fullwidth exclamation
    0xFF1F: "?",   # ？ fullwidth question
    0xFF1A: ":",   # ： fullwidth colon
    0xFF1B: ";",   # ； fullwidth semicolon
    0x3002: ".",   # 。 ideographic full stop
    0xFF08: "(",   # （ fullwidth paren
    0xFF09: ")",   # ） fullwidth paren
    0x2018: "'",   # ‘ curly quote
    0x2019: "'",   # ’ curly quote
    0x201C: '"',   # “ curly quote
    0x201D: '"',   # ” curly quote
    0x2010: "-", 0x2011: "-", 0x2012: "-", 0x2013: "-", 0x2014: "-", 0x2015: "-",
    0x2026: "...", # … ellipsis
}

def is_allowed(ch):
    cp = ord(ch)
    if ch in "\n\r\t":
        return True
    if ch in ALLOWED_EXPLICIT:
        return True
    for lo, hi in ALLOWED_RANGES:
        if lo <= cp <= hi:
            return True
    return False

def char_label(ch):
    cp = ord(ch)
    try:
        name = unicodedata.name(ch)
    except ValueError:
        name = "<unnamed>"
    return f"U+{cp:04X} {name}"

def clean_string(s):
    """Возвращает (очищенную строку, Counter мусорных символов)."""
    junk = Counter()
    out = []
    for ch in s:
        cp = ord(ch)
        if cp in CHAR_MAP:
            # 22.09: замена на эквивалент (учёт как правка, не мусор)
            out.append(CHAR_MAP[cp])
            junk[char_label(ch) + " -> замена"] += 1
        elif is_allowed(ch):
            out.append(ch)
        else:
            junk[char_label(ch)] += 1
    cleaned = "".join(out)
    # Схлопывание лишних пробелов на месте удалённых символов не делаем,
    # но убираем двойные пробелы, появившиеся от склейки
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r" +\n", "\n", cleaned)
    return cleaned, junk

def iter_files(root):
    if os.path.isfile(root):
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in (".txt", ".md", ".docx") and not fn.endswith(".bak"):
                yield os.path.join(dirpath, fn)

def clean_docx(path, apply):
    """Чистит word/document.xml внутри docx. Возвращает (junk, changed)."""
    junk_total = Counter()
    changed = False
    try:
        with zipfile.ZipFile(path, "r") as zin:
            names = zin.namelist()
            data = {n: zin.read(n) for n in names}
    except zipfile.BadZipFile:
        return {"<BAD ZIP>": 1}, False

    for name in names:
        if name != "word/document.xml":
            continue
        xml = data[name].decode("utf-8")
        # Чистим только текст внутри <w:t>...</w:t>, XML-теги не трогаем
        def repl(m):
            nonlocal junk_total, changed
            text = m.group(2)
            cleaned, junk = clean_string(text)
            if junk:
                junk_total.update(junk)
                changed = True
            return m.group(1) + cleaned + m.group(3)
        new_xml = re.sub(r"(<w:t[^>]*>)(.*?)(</w:t>)", repl, xml, flags=re.DOTALL)
        if changed:
            data[name] = new_xml.encode("utf-8")

    if apply and changed:
        shutil.copy2(path, path + ".bak")
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zout:
            for n in names:
                zout.writestr(n, data[n])
    return junk_total, changed

def clean_text_file(path, apply):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    cleaned, junk = clean_string(content)
    if junk and apply:
        shutil.copy2(path, path + ".bak")
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(cleaned)
    return junk

def main():
    args = [a for a in sys.argv[1:] if a != "--fix"]
    apply = "--fix" in sys.argv
    if not args:
        print(__doc__)
        sys.exit(1)
    root = args[0]
    if not os.path.exists(root):
        print(f"Путь не найден: {root}")
        sys.exit(1)

    mode = "FIX (бэкапы .bak)" if apply else "ОТЧЁТ (ничего не меняется, добавь --fix)"
    print(f"Режим: {mode}\n")

    total_files = 0
    total_junk = 0
    for path in iter_files(root):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".docx":
            junk, changed = clean_docx(path, apply)
        else:
            junk = clean_text_file(path, apply)
            changed = bool(junk)
        if junk:
            total_files += 1
            n = sum(junk.values())
            total_junk += n
            status = "ОЧИЩЕН" if (apply and changed) else "найден мусор"
            print(f"[{status}] {path} — {n} симв.")
            for label, cnt in junk.most_common(5):
                print(f"    {cnt:5d} x {label}")
            if len(junk) > 5:
                print(f"    ... и ещё {len(junk) - 5} типов")

    print(f"\nИтого: файлов с мусором: {total_files}, мусорных символов: {total_junk}")
    if not apply and total_junk:
        print("Для очистки запусти с --fix")

if __name__ == "__main__":
    main()