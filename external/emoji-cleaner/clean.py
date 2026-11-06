# -*- coding: utf-8 -*-
# Чистка документов от эмодзи и текстовых смайлов, которые добавляют нейросети (ChatGPT, DeepSeek и др.)
# Форматы: .txt .md .markdown .docx
#
# Использование:
#   python clean.py <путь> [путь2 ...] [--dry-run] [--backup] [--restore]
#   путь может быть файлом или папкой (папка чистится рекурсивно)
#   --dry-run  только показать, что удалится (файлы не меняются)
#   --backup   перед изменением сохранить копию <файл>.bak
#   --restore  откатить изменения из копий <файл>.bak (копии не удаляются)
#
# Гарантии целостности:
#   - docx: правка на уровне XML w:t (только текст) - жирный/курсив/подчёркивание,
#     таблицы (любая вложенность), текстбоксы, сноски, колонтитулы, комментарии не ломаются
#   - md: блоки кода (``` / ~~~) и inline-код (`...`) не трогаются на предмет пробелов и смайлов
#   - отступы строк и CRLF сохраняются, BOM сохраняется, cp1251 читается/пишется родной кодировкой
#   - бинарные файлы (с \x00) пропускаются
#   - URL (https://...) не задеваются текстовыми смайлами
#   - НЕ удаляются легитимные символы: шахматные фигуры, ноты, масти карт, игральные кости
#   - md hard-break (2 пробела в конце строки) не убивается

import re
import sys
import shutil
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv
BACKUP = "--backup" in sys.argv
RESTORE = "--restore" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]

if BACKUP and RESTORE:
    print("Несовместимо: --backup и --restore одновременно.")
    sys.exit(1)
if not args:
    print("Использование: python clean.py <файл или папка> [...] [--dry-run] [--backup] [--restore]")
    sys.exit(1)

# --- Эмодзи (Unicode-диапазоны) ---
# Намеренно НЕ трогаем: шахматы 2654-265F, ноты 2669-266F, масти 2660-2668, кости 2680-2685,
# символы Mac 2300-2319, BOM \uFEFF
EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"      # основное эмодзи-множество + доп. символы и пиктограммы
    "\u2190-\u21FF"               # стрелки (нейросети любят ->)
    "\u2600-\u2653"               # разн. символы (погода, знаки, люди) - до шахмат
    "\u2670-\u267F"               # переработка и др.
    "\u2686-\u27BF"               # динбаты: галочки, крестики, знаки, сердца
    "\u2B00-\u2BFF"               # стрелки-A, звёзды
    "\u25A0-\u25FF"               # геометрические фигуры (квадраты-маркеры)
    "\u231A\u231B\u23E9-\u23FA"   # часы/таймеры (узко, чтобы не задеть символы Mac)
    "\u2139\u24C2\u203C\u2049"    # i, M, !!, !? - эмодзи вне основных блоков
    "\u2934\u2935\u3030"          # стрелки-углы, волнистая черта
    "\uFE0F\uFE0E"                # селекторы вариантов
    "\u200D\u200C\u200B"          # ZWJ ZWNJ ZWSP
    "\u20E3"                      # keycap
    "]"
)

# служебные коды эмодзи-последовательностей: не считаем самостоятельными эмодзи
EMOJI_JOINERS = frozenset("\u200D\u200C\u200B\uFE0F\uFE0E\u20E3")

# --- Текстовые смайлы: :) :-) :D ;) :( :/ :| :P :O :3 и ^_^ T_T o_o 0_0 ---
# Глаза только : ; = (без 8 x X - они дают ложные срабатывания на "из 8)").
# Перед смайлом требуется начало строки/пробел/скобка - чтобы не задеть URL и "10:5".
SMILEY_RE = re.compile(
    r"(?:(?<=^)|(?<=[\s(\[]))"
    r"(?:[:;=][\-o\*']?[)(\]/DPp3Oo|]"
    r"|\^_\^|T_T|o_o|0_0)"
)

FENCE_RE = re.compile(r"^\s*(```|~~~)")   # границы блоков кода в md
INNER_SPACE_RE = re.compile(r"(?<=\S) {2,}(?=\S)")  # двойные пробелы только МЕЖДУ словами
PUNCT_FIX_RE = re.compile(r" ([,.!?;:%)])")          # пробел перед знаком препинания


def strip_emoji(text, samples=None):
    """Удалить эмодзи. Служебные коды (ZWJ, селекторы) удаляются, но в счётчик не идут.
    Возвращает (текст, кол-во)."""
    matches = EMOJI_RE.findall(text)
    n = 0
    if matches:
        for m in matches:
            if m in EMOJI_JOINERS:
                continue
            n += 1
            if samples is not None:
                samples.add(m)
        text = EMOJI_RE.sub("", text)
    return text, n


def strip_smileys(text):
    """Удалить текстовые смайлы. Возвращает (текст, кол-во)."""
    n = len(SMILEY_RE.findall(text))
    if n:
        text = SMILEY_RE.sub("", text)
    return text, n


# ---------- TXT / MD ----------

def clean_outside(seg, samples, in_fence):
    """Чистка сегмента строки.
    Вне блоков кода: эмодзи + смайлы + уборка пробелов.
    Внутри блока кода (```): только эмодзи, смайлы/пробелы не трогаем."""
    orig = seg
    seg, e = strip_emoji(seg, samples)
    if in_fence:
        return seg, e, 0
    seg, s = strip_smileys(seg)
    if e or s:
        seg = INNER_SPACE_RE.sub(" ", seg)
        seg = PUNCT_FIX_RE.sub(r"\1", seg)
        # хвостовые пробелы убираем, только если их не было в оригинале
        # (2 пробела в конце строки = md hard-break, его сохраняем)
        if orig == orig.rstrip():
            seg = seg.rstrip()
    return seg, e, s


def clean_plain(path, samples):
    """Чистка txt/md построчно.
    - md: блоки кода (``` / ~~~) и inline-код (`...`) защищены от смайлов и правки пробелов
    - CRLF сохраняется (\\r в конце строк не трогаем)
    - бинарные файлы (с \\x00) пропускаются"""
    raw = path.read_bytes()
    if b"\x00" in raw:
        print(f"Пропущен (бинарный файл): {path.name}")
        return False, 0, 0
    is_md = path.suffix.lower() in (".md", ".markdown")
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    body = raw[3:] if had_bom else raw
    try:
        text = body.decode("utf-8")
        enc = "utf-8"
    except UnicodeDecodeError:
        text = body.decode("cp1251")
        enc = "cp1251"

    lines = text.split("\n")
    in_fence = False
    e_total = s_total = 0
    out_lines = []
    for line in lines:
        cr = line.endswith("\r")            # Windows CRLF: \r не входит в чистку
        core = line[:-1] if cr else line
        if FENCE_RE.match(core):
            in_fence = not in_fence
            out_lines.append(core + ("\r" if cr else ""))
            continue
        if is_md and "`" in core:
            # inline-код `...`: чётные сегменты = текст, нечётные = код (эмодзи убираем,
            # смайлы и пробелы в коде не трогаем)
            parts = core.split("`")
            for i in range(0, len(parts), 2):
                new, e, s = clean_outside(parts[i], samples, in_fence)
                e_total += e
                s_total += s
                parts[i] = new
            for i in range(1, len(parts), 2):
                parts[i], e = strip_emoji(parts[i], samples)
                e_total += e
            new = "`".join(parts)
        else:
            new, e, s = clean_outside(core, samples, in_fence)
            e_total += e
            s_total += s
        out_lines.append(new + ("\r" if cr else ""))

    if not (e_total or s_total):
        return False, 0, 0
    if not DRY_RUN:
        if BACKUP:
            shutil.copy2(path, str(path) + ".bak")
        data = ("\n".join(out_lines)).encode(enc)
        if had_bom:
            data = b"\xef\xbb\xbf" + data
        path.write_bytes(data)
    return True, e_total, s_total


# ---------- DOCX ----------

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
# части пакета, где есть текст пользователя
DOC_PART_KEYWORDS = ("document", "header", "footer", "footnotes", "endnotes", "comments")


def clean_wt_element(t_el, samples):
    """Чистка одного w:t. Меняем ТОЛЬКО текст - rPr (жирный/курсив) неприкосновенны.
    Возвращает (кол-во_эмодзи, кол-во_смайлов)."""
    txt = t_el.text
    if not txt:
        return 0, 0
    new, e = strip_emoji(txt, samples)
    new, s = strip_smileys(new)
    if not (e or s):
        return 0, 0
    # двойные пробелы/пробел перед знаком - только внутри текста run'а;
    # ведущие/хвостовые пробелы НЕ трогаем (в docx они значимы, xml:space="preserve")
    new = INNER_SPACE_RE.sub(" ", new)
    new = PUNCT_FIX_RE.sub(r"\1", new)
    t_el.text = new
    if new != new.strip():
        # есть краевые пробелы - без этого атрибута Word их съест
        t_el.set(XML_SPACE, "preserve")
    return e, s


def clean_docx(path, samples):
    """Чистка docx на уровне XML: тело, таблицы (любая вложенность), текстбоксы,
    сноски, колонтитулы, комментарии. Форматирование сохраняется полностью."""
    from docx import Document
    from lxml import etree

    doc = Document(path)
    e_total = s_total = 0

    for part in doc.part.package.iter_parts():
        name = str(part.partname)
        if "/word/" not in name:
            continue
        if not any(k in name for k in DOC_PART_KEYWORDS):
            continue

        el = getattr(part, "_element", None)   # часть, распарсенная python-docx
        parsed_blob = False
        if el is None:
            blob = part.blob or b""
            if b"<w:" not in blob:
                continue
            try:
                el = etree.fromstring(blob)
                parsed_blob = True
            except etree.XMLSyntaxError:
                continue

        e = s = 0
        for t_el in el.iter(W_NS + "t"):
            de, ds = clean_wt_element(t_el, samples)
            e += de
            s += ds
        e_total += e
        s_total += s

        if parsed_blob and (e or s):
            # нестандартная часть (сноски и т.п.) - пишем обратно сериализованный XML
            part._blob = etree.tostring(el, xml_declaration=True,
                                        encoding="UTF-8", standalone=True)

    if not DRY_RUN and (e_total or s_total):
        if BACKUP:
            shutil.copy2(path, str(path) + ".bak")
        doc.save(path)
    return (e_total or s_total) > 0, e_total, s_total


# ---------- Общее ----------

PLAIN_EXTS = (".txt", ".md", ".markdown", ".docx")


def collect_files():
    """Файлы из аргументов (файл или папка рекурсивно)."""
    files = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            for ext in ("*.txt", "*.md", "*.markdown", "*.docx"):
                files.extend(p.rglob(ext))
        elif p.is_file() and p.suffix.lower() in PLAIN_EXTS:
            files.append(p)
        else:
            print(f"Пропущено (не найдено или не тот формат): {a}")
    seen, out = set(), []
    for f in files:
        if ".git" in f.parts:
            continue
        key = str(f.resolve()).lower()
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def collect_bak_files():
    """Копии .bak из аргументов: папка -> все *.bak, файл -> его .bak."""
    baks = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            baks.extend(p.rglob("*.bak"))
        elif str(p).lower().endswith(".bak") and p.is_file():
            baks.append(p)
        elif p.is_file():
            cand = Path(str(p) + ".bak")
            if cand.is_file():
                baks.append(cand)
            else:
                print(f"Нет копии для: {a}")
        else:
            print(f"Пропущено: {a}")
    seen, out = set(), []
    for b in baks:
        if ".git" in b.parts:
            continue
        key = str(b.resolve()).lower()
        if key not in seen:
            seen.add(key)
            out.append(b)
    return out


def restore_backups():
    """Откат из .bak. Копии не удаляются (удаление - только вручную)."""
    baks = collect_bak_files()
    if not baks:
        print("Копии .bak не найдены.")
        sys.exit(1)
    done = 0
    for b in baks:
        orig = Path(str(b)[:-4])
        if not orig.exists():
            print(f"Оригинал не найден для: {b.name}")
            continue
        if DRY_RUN:
            print(f"[DRY-RUN] восстановлено бы: {orig.name}")
        else:
            shutil.copy2(b, orig)
            print(f"Восстановлено: {orig.name}")
        done += 1
    print(f"\nИтого: копий {len(baks)}, восстановлено {done}.")
    if not DRY_RUN:
        print("Копии .bak оставлены - удалите вручную, когда всё проверите.")


def main():
    files = collect_files()
    if not files:
        print("Файлы не найдены.")
        sys.exit(1)

    total_changed = total_emoji = total_smile = 0
    for f in files:
        samples = set()
        try:
            if f.suffix.lower() == ".docx":
                changed, ne, ns = clean_docx(f, samples)
            else:
                changed, ne, ns = clean_plain(f, samples)
        except Exception as exc:
            print(f"ОШИБКА {f.name}: {exc}")
            continue
        if changed:
            total_changed += 1
            total_emoji += ne
            total_smile += ns
            mode = "[DRY-RUN] " if DRY_RUN else ""
            line = f"{mode}{f.name}: эмодзи {ne}, смайлов {ns}"
            if DRY_RUN and samples:
                preview = " ".join(sorted(samples)[:12])
                line += f"\n           примеры: {preview}"
            print(line)

    print(f"\nИтого: файлов {len(files)}, изменено {total_changed}, "
          f"эмодзи удалено {total_emoji}, смайлов удалено {total_smile}")
    if DRY_RUN:
        print("Режим dry-run - файлы НЕ изменены.")
    elif BACKUP and total_changed:
        print("Копии изменённых файлов: <имя>.bak")


if __name__ == "__main__":
    if RESTORE:
        restore_backups()
    else:
        main()