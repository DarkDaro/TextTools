# -*- coding: utf-8 -*-
# Чистка документов от эмодзи и текстовых смайлов, которые добавляют нейросети (ChatGPT, DeepSeek и др.)
# Форматы: .txt .md .markdown .docx
#
# Использование:
#   python clean.py <путь> [путь2 ...] [--dry-run] [--backup] [--restore]
#                  [--invisible] [--ws] [--ai-scan] [--json out.json]
#   путь может быть файлом или папкой (папка чистится рекурсивно)
#   --dry-run    только показать, что удалится (файлы не меняются)
#   --backup     перед изменением сохранить копию <файл>.bak
#   --restore    откатить изменения из копий <файл>.bak (копии не удаляются)
#
#   21.11 — следы ИИ (можно сочетать с чисткой и --dry-run):
#   --invisible  чистка невидимых символов: нулевые (ZWSP/ZWNJ/ZWJ/WJ,
#                BOM в тексте), двунаправленные метки, тег-символы
#                (носители водяных знаков ИИ), мягкий перенос.
#                В код-блоках и inline-коде тоже — там им не место
#   --ws         нормализация пробелов и табуляции: табы между словами
#                → один пробел, необычные unicode-пробелы → обычный.
#                Ведущие отступы и md hard-break не трогаются
#   --ai-scan    ТОЛЬКО ЧТЕНИЕ: отчёт о следах ИИ в файлах — невидимые
#                символы по категориям, слова с подменой алфавита
#                (латиница/кириллица вперемешку), в docx — скрытый и
#                белый текст. Код выхода: 0 — чисто, 1 — есть следы
#   --json F     с --ai-scan: отчёт в JSON
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

import json

# 21.11: разбор аргументов с учётом флага-значения (--json <файл>)
argv = sys.argv[1:]
DRY_RUN = "--dry-run" in argv
BACKUP = "--backup" in argv
RESTORE = "--restore" in argv
INVISIBLE = "--invisible" in argv   # чистка невидимых символов
WS = "--ws" in argv                 # нормализация табов и пробелов
AISCAN = "--ai-scan" in argv        # только чтение: отчёт о следах ИИ
JSON_OUT = ""
_args = []
_skip = False
for _i, _a in enumerate(argv):
    if _skip:
        _skip = False
        continue
    if _a == "--json":
        JSON_OUT = argv[_i + 1] if _i + 1 < len(argv) else ""
        _skip = True
        continue
    _args.append(_a)
args = [a for a in _args if not a.startswith("--")]

if BACKUP and RESTORE:
    print("Несовместимо: --backup и --restore одновременно.")
    sys.exit(1)
if RESTORE and (INVISIBLE or WS or AISCAN):
    print("Несовместимо: --restore не сочетается с чисткой и --ai-scan.")
    sys.exit(1)
if not args:
    print("Использование: python clean.py <файл или папка> [...] "
          "[--dry-run] [--backup] [--restore] [--invisible] [--ws] [--ai-scan]")
    sys.exit(1)
if AISCAN and (DRY_RUN or BACKUP):
    print("--ai-scan — только чтение, --dry-run/--backup игнорируются.")

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

# --- Невидимые символы и следы ИИ (21.11) ---
# То, чего эмодзи-чистка не видит: нулевые символы, двунаправленные
# метки, тег-символы (типовой носитель водяных знаков ИИ), мягкий
# перенос. --invisible убирает их, --ai-scan — читает и сообщает.
INVISIBLE_MAP = (
    ("zw",   re.compile("[\u180E\u200B\u200C\u200D\u2060-\u2064\uFEFF]"), "",
     "нулевые символы (ZWSP, ZWNJ, ZWJ, WJ, BOM в тексте)"),
    ("bidi", re.compile("[\u061C\u200E\u200F\u202A-\u202E\u2066-\u2069]"), "",
     "двунаправленные и изолирующие метки"),
    ("tag",  re.compile("[\U000E0000-\U000E007F]"), "",
     "тег-символы - типовой носитель водяных знаков ИИ"),
    ("shy",  re.compile("\u00AD"), "",
     "мягкий перенос"),
)
INVISIBLE_DESC = {name: desc for name, _rx, _repl, desc in INVISIBLE_MAP}

# необычные unicode-пробелы -> обычный (это --ws, не --invisible)
WS_SPACES_RE = re.compile("[\u2000-\u200A\u202F\u205F\u3000]")


def strip_invisible(text, counts=None):
    """Убрать невидимые символы. counts - словарь "категория -> кол-во".
    Возвращает (текст, counts)."""
    if counts is None:
        counts = {}
    for name, rx, repl, _desc in INVISIBLE_MAP:
        n = len(rx.findall(text))
        if n:
            counts[name] = counts.get(name, 0) + n
            text = rx.sub(repl, text)
    return text, counts


# --- нормализация пробелов и табуляции (--ws) ---
TAB_BETWEEN_RE = re.compile(r"(?<=\S)\t+(?=\S)")  # табы между словами


def normalize_ws_core(seg):
    """Табы между видимыми символами -> один пробел, необычные
    unicode-пробелы -> обычный. Ведущие отступы и хвостовые пробелы
    (в т.ч. md hard-break) не трогаются. Возвращает (текст, кол-во)."""
    n = 0
    seg, k = TAB_BETWEEN_RE.subn(" ", seg)
    n += k
    seg, k = WS_SPACES_RE.subn(" ", seg)
    n += k
    return seg, n

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
    Вне блоков кода: эмодзи + смайлы + уборка пробелов; с --ws ещё табы
    между словами и необычные пробелы. Внутри блока кода (```): эмодзи
    всегда, с --invisible - невидимые тоже (в коде им не место),
    смайлы/табы/пробелы не трогаем.
    Возвращает (текст, эмодзи, смайлы, ws-замен, невидимых)."""
    orig = seg
    seg, e = strip_emoji(seg, samples)
    inv = {}
    if INVISIBLE:
        seg, inv = strip_invisible(seg)
    if in_fence:
        return seg, e, 0, 0, inv
    seg, s = strip_smileys(seg)
    ws_n = 0
    if WS:
        seg, ws_n = normalize_ws_core(seg)
    if e or s or ws_n or inv:
        seg = INNER_SPACE_RE.sub(" ", seg)
        seg = PUNCT_FIX_RE.sub(r"\1", seg)
        # хвостовые пробелы убираем, только если их не было в оригинале
        # (2 пробела в конце строки = md hard-break, его сохраняем)
        if orig == orig.rstrip():
            seg = seg.rstrip()
    return seg, e, s, ws_n, inv


def clean_plain(path, samples):
    """Чистка txt/md построчно.
    - md: блоки кода (``` / ~~~) и inline-код (`...`) защищены от смайлов и правки пробелов
    - с --invisible невидимые убираются и в коде; с --ws табы/необычные
      пробелы - только вне кода
    - CRLF сохраняется (\\r в конце строк не трогаем)
    - бинарные файлы (с \\x00) пропускаются
    Возвращает (изменён, эмодзи, смайлы, ws-замен, невидимых-словарь)"""
    raw = path.read_bytes()
    if b"\x00" in raw:
        print(f"Пропущен (бинарный файл): {path.name}")
        return False, 0, 0, 0, {}
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
    e_total = s_total = ws_total = 0
    inv_total = {}
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
            # смайлы и пробелы в коде не трогаем; невидимые - по флагу)
            parts = core.split("`")
            for i in range(0, len(parts), 2):
                new, e, s, wsn, inv = clean_outside(parts[i], samples, in_fence)
                e_total += e
                s_total += s
                ws_total += wsn
                for k, v in inv.items():
                    inv_total[k] = inv_total.get(k, 0) + v
                parts[i] = new
            for i in range(1, len(parts), 2):
                parts[i], e = strip_emoji(parts[i], samples)
                e_total += e
                if INVISIBLE:
                    parts[i], inv = strip_invisible(parts[i])
                    for k, v in inv.items():
                        inv_total[k] = inv_total.get(k, 0) + v
            new = "`".join(parts)
        else:
            new, e, s, wsn, inv = clean_outside(core, samples, in_fence)
            e_total += e
            s_total += s
            ws_total += wsn
            for k, v in inv.items():
                inv_total[k] = inv_total.get(k, 0) + v
        out_lines.append(new + ("\r" if cr else ""))

    if not (e_total or s_total or ws_total or inv_total):
        return False, 0, 0, 0, {}
    if not DRY_RUN:
        if BACKUP:
            shutil.copy2(path, str(path) + ".bak")
        data = ("\n".join(out_lines)).encode(enc)
        if had_bom:
            data = b"\xef\xbb\xbf" + data
        path.write_bytes(data)
    return True, e_total, s_total, ws_total, inv_total


# ---------- DOCX ----------

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
# части пакета, где есть текст пользователя
DOC_PART_KEYWORDS = ("document", "header", "footer", "footnotes", "endnotes", "comments")


def clean_wt_element(t_el, samples):
    """Чистка одного w:t. Меняем ТОЛЬКО текст - rPr (жирный/курсив) неприкосновенны.
    Возвращает (кол-во_эмодзи, кол-во_смайлов, ws-замен, невидимых-словарь)."""
    txt = t_el.text
    if not txt:
        return 0, 0, 0, {}
    new, e = strip_emoji(txt, samples)
    if INVISIBLE:
        new, inv = strip_invisible(new)
    else:
        inv = {}
    new, s = strip_smileys(new)
    ws_n = 0
    if WS:
        new, ws_n = normalize_ws_core(new)
    if not (e or s or ws_n or inv):
        return 0, 0, 0, {}
    # двойные пробелы/пробел перед знаком - только внутри текста run'а;
    # ведущие/хвостовые пробелы НЕ трогаем (в docx они значимы, xml:space="preserve")
    new = INNER_SPACE_RE.sub(" ", new)
    new = PUNCT_FIX_RE.sub(r"\1", new)
    t_el.text = new
    if new != new.strip():
        # есть краевые пробелы - без этого атрибута Word их съест
        t_el.set(XML_SPACE, "preserve")
    return e, s, ws_n, inv


def clean_docx(path, samples):
    """Чистка docx на уровне XML: тело, таблицы (любая вложенность), текстбоксы,
    сноски, колонтитулы, комментарии. Форматирование сохраняется полностью."""
    from docx import Document
    from lxml import etree

    doc = Document(path)
    e_total = s_total = ws_total = 0
    inv_total = {}

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

        e = s = wsn = 0
        for t_el in el.iter(W_NS + "t"):
            de, ds, dws, dinv = clean_wt_element(t_el, samples)
            e += de
            s += ds
            wsn += dws
            for k, v in dinv.items():
                inv_total[k] = inv_total.get(k, 0) + v
        e_total += e
        s_total += s
        ws_total += wsn

        if parsed_blob and (e or s):
            # нестандартная часть (сноски и т.п.) - пишем обратно сериализованный XML
            part._blob = etree.tostring(el, xml_declaration=True,
                                        encoding="UTF-8", standalone=True)

    if not DRY_RUN and (e_total or s_total or ws_total or inv_total):
        if BACKUP:
            shutil.copy2(path, str(path) + ".bak")
        doc.save(path)
    return ((e_total or s_total or ws_total or inv_total) > 0,
            e_total, s_total, ws_total, inv_total)


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

    total_changed = total_emoji = total_smile = total_ws = 0
    total_inv = {}
    for f in files:
        samples = set()
        try:
            if f.suffix.lower() == ".docx":
                changed, ne, ns, nws, ninv = clean_docx(f, samples)
            else:
                changed, ne, ns, nws, ninv = clean_plain(f, samples)
        except Exception as exc:
            print(f"ОШИБКА {f.name}: {exc}")
            continue
        if changed:
            total_changed += 1
            total_emoji += ne
            total_smile += ns
            total_ws += nws
            for k, v in ninv.items():
                total_inv[k] = total_inv.get(k, 0) + v
            mode = "[DRY-RUN] " if DRY_RUN else ""
            line = f"{mode}{f.name}: эмодзи {ne}, смайлов {ns}"
            if nws:
                line += f", табов/пробелов {nws}"
            if ninv:
                det = ", ".join(f"{k} {v}" for k, v in sorted(ninv.items()))
                line += f", невидимых {sum(ninv.values())} ({det})"
            if DRY_RUN and samples:
                preview = " ".join(sorted(samples)[:12])
                line += f"\n           примеры: {preview}"
            print(line)

    tail = ""
    if total_ws:
        tail += f", табов/пробелов {total_ws}"
    if total_inv:
        det = ", ".join(f"{k} {v}" for k, v in sorted(total_inv.items()))
        tail += f", невидимых {sum(total_inv.values())} ({det})"
    print(f"\nИтого: файлов {len(files)}, изменено {total_changed}, "
          f"эмодзи удалено {total_emoji}, смайлов удалено {total_smile}{tail}")
    if DRY_RUN:
        print("Режим dry-run - файлы НЕ изменены.")
    elif BACKUP and total_changed:
        print("Копии изменённых файлов: <имя>.bak")


# ---------- Следы ИИ: только чтение (--ai-scan, 21.11) ----------

MIXED_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)  # цепочки букв без цифр


def _script_mixes(word):
    """Слово содержит и кириллицу, и латиницу - верный признак подмены
    символа ( латинская "a" внутри русского слова и т.п.)."""
    has_cyr = has_lat = False
    for ch in word:
        if "\u0400" <= ch <= "\u04FF":
            has_cyr = True
        elif ("A" <= ch <= "Z") or ("a" <= ch <= "z"):
            has_lat = True
    return has_cyr and has_lat


def scan_text_for_ai(text):
    """Скан текста: невидимые по категориям, необычные пробелы,
    слова с подменой алфавита. Возвращает dict с примерами."""
    inv = {}
    mixed = []
    for i, line in enumerate(text.split("\n"), 1):
        for name, rx, _repl, _desc in INVISIBLE_MAP:
            hits = rx.findall(line)
            if hits:
                inv.setdefault(name, []).append(
                    [i, hits[0], len(hits)])
        hits = WS_SPACES_RE.findall(line)
        if hits:
            inv.setdefault("usp", []).append([i, hits[0], len(hits)])
        for w in MIXED_WORD_RE.findall(line):
            if _script_mixes(w):
                mixed.append([w, i])
    return {"invisible": inv, "mixed": mixed}


def scan_plain_ai(path):
    """Скан txt/md. Возвращает (отчёт|None, ошибка|None)."""
    raw = path.read_bytes()
    if b"\x00" in raw:
        return None, "бинарный"
    body = raw[3:] if raw.startswith(b"\xef\xbb\xbf") else raw
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        text = body.decode("cp1251")
    return scan_text_for_ai(text), None


def scan_docx_ai(path):
    """Скан docx: текст всех w:t, скрытые (vanish) и белые runs.
    Возвращает (отчёт|None, ошибка|None)."""
    from docx import Document

    doc = Document(path)
    inv = {}
    mixed = []
    hidden = []
    white = []
    for part in doc.part.package.iter_parts():
        name = str(part.partname)
        if "/word/" not in name:
            continue
        if not any(k in name for k in DOC_PART_KEYWORDS):
            continue
        el = getattr(part, "_element", None)
        if el is None:
            continue
        where = name.split("/")[-1]
        for r_el in el.iter(W_NS + "r"):
            txts = "".join(t.text or "" for t in r_el.iter(W_NS + "t"))
            rpr = r_el.find(W_NS + "rPr")
            if rpr is not None and txts.strip():
                v = rpr.find(W_NS + "vanish")
                if v is not None and str(v.get(W_NS + "val", "")) \
                        not in ("0", "false"):
                    hidden.append([where, txts[:60]])
                c = rpr.find(W_NS + "color")
                if c is not None and str(c.get(W_NS + "val", "")).upper() \
                        in ("FFFFFF", "FEFEFE", "FFFFFE"):
                    white.append([where, txts[:60]])
            if not txts:
                continue
            rep = scan_text_for_ai(txts)
            for k, lst in rep["invisible"].items():
                for _i, sample, cnt in lst:
                    inv.setdefault(k, []).append([where, sample, cnt])
            for w, _i in rep["mixed"]:
                mixed.append([w, where])
    return ({"invisible": inv, "mixed": mixed,
             "hidden": hidden, "white": white}), None


def _inv_summary(inv):
    """Невидимые: {кат: [(где, символ, кол-во)...]} -> строка-итог."""
    by_cat = {}
    for cat, lst in inv.items():
        by_cat[cat] = sum(x[2] for x in lst)
    det = ", ".join(f"{k} {v}" for k, v in sorted(by_cat.items()))
    return sum(by_cat.values()), det


def ai_scan_main():
    """--ai-scan: читает файлы и сообщает о следах ИИ. Ничего не меняет.
    Код выхода: 0 - чисто, 1 - есть следы, 2 - файлы не найдены."""
    files = collect_files()
    if not files:
        print("Файлы не найдены.")
        sys.exit(2)
    dirty = 0
    reports = {}
    for f in files:
        try:
            if f.suffix.lower() == ".docx":
                rep, err = scan_docx_ai(f)
            else:
                rep, err = scan_plain_ai(f)
        except Exception as exc:
            print(f"ОШИБКА {f.name}: {exc}")
            continue
        if err:
            print(f"{f.name}: пропущен ({err})")
            continue
        reports[str(f)] = rep
        n_inv, inv_det = _inv_summary(rep["invisible"])
        n_mix = len(rep.get("mixed", []))
        n_hid = len(rep.get("hidden", []))
        n_wht = len(rep.get("white", []))
        total = n_inv + n_mix + n_hid + n_wht
        if not total:
            print(f"{f.name}: чисто")
            continue
        dirty += 1
        parts = []
        if n_inv:
            parts.append(f"невидимых {n_inv} ({inv_det})")
        if n_mix:
            parts.append(f"подменённых слов {n_mix}")
        if n_hid:
            parts.append(f"скрытых текстов {n_hid}")
        if n_wht:
            parts.append(f"белых текстов {n_wht}")
        print(f"{f.name}: ЕСТЬ СЛЕДЫ - " + ", ".join(parts))
        for cat, lst in sorted(rep["invisible"].items()):
            desc = INVISIBLE_DESC.get(cat, "необычные пробелы")
            where = [str(x[0]) for x in lst[:3]]
            loc = ("строки " + ", ".join(where)
                   if all(w.isdigit() for w in where)
                   else ", ".join(sorted(set(where))))
            print(f"           {desc}: {loc}")
        for w, where in rep.get("mixed", [])[:5]:
            print(f"           подмена: «{w}» ({where})")
        for where, txt in rep.get("hidden", [])[:3]:
            print(f"           скрытый текст ({where}): «{txt}»")
        for where, txt in rep.get("white", [])[:3]:
            print(f"           белый текст ({where}): «{txt}»")
    print(f"\nИтог: файлов {len(reports)}, со следами {dirty}. "
          "Режим чтения - файлы не менялись.")
    if JSON_OUT:
        Path(JSON_OUT).write_text(
            json.dumps({"ok": dirty == 0, "files": reports},
                       ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(f"JSON-отчёт: {JSON_OUT}")
    sys.exit(1 if dirty else 0)


if __name__ == "__main__":
    if RESTORE:
        restore_backups()
    elif AISCAN:
        ai_scan_main()
    else:
        main()