# -*- coding: utf-8 -*-
"""
typography — приведение типографики к русской норме в .md/.txt/.docx.

  python typography.py --input <папка или файл> [--fix] [--nbsp]
      [--check] [--out report.md]

Правила (вне блоков кода ```, frontmatter .md и inline-кода `...`):
  1. «...» (3+ точки) -> «…»; «?...» и «!...» -> «?..» и «!..»
     (после ? и ! по норме ставятся две точки).
  2. «слово - слово» и «слово -- слово» -> «слово — слово»;
     недостающий пробел после тире: «слово —слово» -> «слово — слово»;
     диапазоны лет «1941-1945» -> «1941—1945» и en dash в числах
     «5–7» -> «5—7» (тире без пробелов).
  3. Кавычки: „лапки“ и прямые "..." -> «ёлочки» — только парные в
     пределах строки и только вокруг текста с кириллицей (латиница, URL,
     строки с «=» не трогаются). Вложенная цитата: если «ёлочки» в строке
     уже есть, прямые кавычки становятся внутренними „лапками“.
     Пробелы внутри кавычек убираются: « важно » -> «важно»
     (диалоговое тире после « не трогается: «— Реплика»).
  4. Диалоговое тире в начале строки «- Реплика» -> «— Реплика»
     (только .txt и .docx; в .md начало строки с «- » — это список).
  5. Пунктуация (07.11): пробел перед знаком убирается («слово ,» ->
     «слово,»); пропущенный пробел после , и ; ставится («Да,нет» ->
     «Да, нет»); после . ! ? … пробел ставится только перед ЗАГЛАВНОЙ
     кириллицей, «(» или «—» — латиница и цифры не трогаются
     (сайты, версии, время 12:30); склеенные сокращения «т.е.» ->
     «т. е.»; двойные пробелы между словами сжимаются
     (выравнивание таблиц | не трогается).
  6. С --nbsp: неразрывный пробел после предлогов/союзов (в, и, с, на...),
     после «№» и перед тире (тире примыкает к предыдущему слову);
     инициалы «И. И. Иванов» не отрываются от фамилии; сокращения
     «т. д.», «и др.» держатся вместе; число не отрывается от
     сокращения («1812 г.», «5 тыс.») и от слова («10 лет»).

Режим вычитки (--check): ничего не правит, перечисляет проблемные
места (файл:строка, для docx — абзац) с типом проблемы: прямые
кавычки, ёлочки без пары, двойной пробел, пробел перед знаком,
нет пробела после знака, дефис вместо тире, многоточие из точек,
дефис в диапазоне лет, «?...» вместо «?..», пробел внутри кавычек.

docx: правится только текст w:t; кавычки — в пределах одного w:t
(разорванные форматированием кавычки не трогаются — это безопаснее).

По умолчанию dry-run (ничего не меняет). С --fix — правит файлы,
создавая <имя>.bak рядом. С --check — только вычитка.
"""
import argparse
import re
# 26.10: shutil не используется (мёртвый импорт) — отключён
# import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.report import write_report
from core import text_parser as tp

SKIP_DIRS = {".git", ".obsidian", ".trash", "reports", "__pycache__",
             "md_replace_backups", ".smart-env"}  # 20.10: бэкапы не трогаем
EXTS = (".md", ".txt", ".docx")
FENCE_RE = ("```", "~~~")

RE_DOTS = re.compile(r"\.{3,}")
RE_DASH_SP = re.compile(r"(?<=\S) - (?=\S)")            # слово - слово
RE_DASH_DB = re.compile(r"(?<=\S)(?: -- |--)(?=\S)")    # слово -- слово
# недостающий пробел после тире: «—слово» / «слово —слово»
RE_DASH_GAP = re.compile(r"(?<=\s)—(?=\S)")
RE_DIALOG = re.compile(r"^(\s*)- (?=\S)")               # «- Реплика» (txt/docx)
# «лапки» — внешние кавычки по русской норме это «ёлочки»
RE_LAPKI = re.compile(r"„([^“\"]*)“")
RE_URL = re.compile(r"https?://|www\.|\]\(")            # ссылки не трогаем
RE_CYR = re.compile(r"[А-Яа-яЁё]")
# 07.11: пробел сразу после открывающей кавычки / перед закрывающей;
# тире и дефис рядом не трогаем (диалог «— Реплика» в кавычках)
RE_Q_SPACE_OPEN = re.compile(r"(«|„) +(?=[^\s—–-])")
RE_Q_SPACE_CLOSE = re.compile(r"(?<=[^\s—–-]) +(»|“)")
# короткие предлоги/союзы, после которых ставится неразрывный пробел
NBSP_WORDS = ("в", "и", "с", "к", "о", "у", "а", "но", "не", "ни", "на",
              "по", "за", "из", "от", "до", "об", "для", "при", "над",
              "под", "как", "что", "же", "ли", "бы", "б")
RE_NBSP = re.compile(
    r"(?<![\wА-Яа-яЁё-])(" + "|".join(NBSP_WORDS) + r") (?=\S)",
    re.IGNORECASE)
RE_NBSP_NUM = re.compile(r"(№) (?=\S)")
# тире не отрывается от предыдущего слова: пробел перед « — » неразрывный
RE_NBSP_DASH = re.compile(r"(?<=\S) (?=—(?:\s|$))")
# инициалы: «И. И.» держатся вместе, «И.» не отрывается от фамилии
RE_NBSP_INIT1 = re.compile(r"(?<=[А-ЯЁ])\. (?=[А-ЯЁ])")
RE_NBSP_INIT2 = re.compile(r"(?<=[А-ЯЁ]\.) (?=[А-ЯЁ][а-яё])")
# сокращения держатся вместе: «т. д.», «и др.», «т. е.»…
NBSP_ABBR = ("и др.", "и пр.", "и т. д.", "и т. п.", "и т. ч.",
             "т. д.", "т. п.", "т. ч.", "т. е.", "т. к.", "т. н.", "т. о.")
RE_NBSP_ABBR = re.compile(
    r"(?<![\wА-Яа-яЁё-])(" + "|".join(re.escape(a) for a in NBSP_ABBR)
    + r")")
# число не отрывается от сокращения: «1812 г.», «5 тыс.», «100 руб.»
RE_NBSP_NUM_ABBR = re.compile(
    r"(?<=\d) (гг?\.|тыс\.|руб\.|коп\.|млн|млрд|стр\.|вв\.)")
# число не отрывается от слова: «10 лет», «12 марта»
RE_NBSP_NUM_WORD = re.compile(r"(?<=\d) (?=[А-Яа-яЁёA-Za-z«])")

# --- пунктуация (07.11): пробелы вокруг знаков, двойные пробелы ---
# «слово ,» -> «слово,» — пробел перед знаком не нужен; «)» после
# знака не даёт править — это смайлик «:)»
RE_PUNCT_BEFORE = re.compile(r"(?<=\S) +([,.;:!?…])(?!\))")
# «Да,нет» -> «Да, нет» — пропущенный пробел после , и ;
RE_PUNCT_AFTER_COMMA = re.compile(r"([,;])(?=[А-Яа-яЁё«(])")
# «слово.Слово» -> «слово. Слово» — после . ! ? … пробел ставится
# только перед заглавной кириллицей, «(» или «—»; латиница и цифры
# не трогаются (сайты, версии «1.2.3», время «12:30»); смайлик «:))»
# защищён — «(» с «)» следом не считается началом фразы
RE_PUNCT_AFTER_SENT = re.compile(r"([.!?…])(?=\((?!\))|[А-ЯЁ«—])")
# склеенные сокращения: «т.е.» -> «т. е.» (то есть, так как и пр.)
RE_ABBR_GLUE = re.compile(r"(?<![\wА-Яа-яЁё])т\.(?=[дпченкос]\.)")
# двойные пробелы между словами (не в начале строки; выравнивание
# таблиц | не трогаем)
RE_MULTI_SP = re.compile(r"(?<=\S) {2,}(?=[^\s|])")

# --- диапазоны (07.11) ---
# годы: «1941-1945» -> «1941—1945» (тире без пробелов; телефоны
# вроде «123-45-67» — короткие сегменты — не задеваются)
RE_RANGE_YEARS = re.compile(r"(?<=\d{4})-(?=\d{4})")
# en dash в числах: «5–7» -> «5—7»
RE_RANGE_ENDASH = re.compile(r"(?<=\d)–(?=\d)")
# «?...» -> «?..»: после ? и ! по норме две точки
RE_DOTS_AFTER = re.compile(r"([?!])(\.{3,})")

RULE_KEYS = ("dots", "dash", "quotes", "punct", "nbsp")
RULE_TITLES = {"dots": "многоточия", "dash": "тире и диапазоны",
               "quotes": "«ёлочки»", "punct": "пунктуация",
               "nbsp": "неразрывные пробелы"}


def _quotes(seg):
    """Кавычки -> «ёлочки». Возвращает (новый_фрагмент, пар).

    «лапки» „...“ заменяются на «ёлочки»; прямые кавычки "..." — тоже,
    но если во фрагменте уже есть «ёлочки» (вложенная цитата), прямые
    становятся внутренними „лапками“ — по правилам русской типографики."""
    # 1) „лапки“ -> «ёлочки» (простая обёртка, содержимое не трогаем)
    seg, k = RE_LAPKI.subn(r"«\1»", seg)
    n = k
    n_q = seg.count('"')
    if n_q == 0 or n_q % 2:
        return seg, n
    # защита: строки с «=» (yaml/html-атрибуты), ссылки, пустые пары
    if "=" in seg or RE_URL.search(seg):
        return seg, n
    parts = seg.split('"')
    contents = parts[1::2]
    if any(not c or not RE_CYR.search(c) for c in contents):
        return seg, n
    # вложенная цитата: «ёлочки» уже есть — прямые кавычки станут „лапками“
    outer = "«" in seg
    op, cl = ("„", "“") if outer else ("«", "»")
    out = [parts[0]]
    for i, c in enumerate(contents):
        out.append(op if i % 2 == 0 else cl)
        out.append(c)
        out.append(cl if i % 2 == 0 else op)
    return "".join(out) + parts[-1], n + len(contents)


def _nbsp(seg):
    """Неразрывные пробелы: предлоги/союзы, №, тире, инициалы,
    сокращения («т. д.»), число + сокращение/слово."""
    n = 0
    # инициалы: «И. И.» вместе, «И.» не отрывается от фамилии
    seg, k = RE_NBSP_INIT1.subn(".\u00A0", seg)
    n += k
    seg, k = RE_NBSP_INIT2.subn("\u00A0", seg)
    n += k
    # сокращения: «т. д.», «и др.» — внутренние пробелы неразрывные;
    # счёт — по вставленным пробелам (в «и т. д.» их два), не по совпадениям
    n += sum(m.group(1).count(" ") for m in RE_NBSP_ABBR.finditer(seg))
    seg = RE_NBSP_ABBR.sub(
        lambda m: m.group(1).replace(" ", "\u00A0"), seg)
    # число + сокращение: «1812 г.», «5 тыс.»
    seg, k = RE_NBSP_NUM_ABBR.subn(
        lambda m: "\u00A0" + m.group(1), seg)
    n += k
    # число + слово: «10 лет», «12 марта»
    seg, k = RE_NBSP_NUM_WORD.subn("\u00A0", seg)
    n += k
    seg, k = RE_NBSP.subn(lambda m: m.group(1) + "\u00A0", seg)
    n += k
    seg, k = RE_NBSP_NUM.subn(lambda m: m.group(1) + "\u00A0", seg)
    n += k
    seg, k = RE_NBSP_DASH.subn("\u00A0", seg)
    n += k
    return seg, n


def _punct(seg, counts):
    """Пунктуация (07.11): пробелы вокруг знаков, склеенные сокращения,
    двойные пробелы. Латиница/цифры после точки не трогаются —
    сайты, версии, время."""
    seg, k = RE_ABBR_GLUE.subn("т. ", seg)
    counts["punct"] += k
    seg, k = RE_PUNCT_BEFORE.subn(r"\1", seg)
    counts["punct"] += k
    seg, k = RE_PUNCT_AFTER_COMMA.subn(r"\1 ", seg)
    counts["punct"] += k
    seg, k = RE_PUNCT_AFTER_SENT.subn(r"\1 ", seg)
    counts["punct"] += k
    seg, k = RE_MULTI_SP.subn(" ", seg)
    counts["punct"] += k
    return seg


def _apply_inline(seg, nbsp, dialogue, counts):
    """Правила для одного фрагмента вне inline-кода."""
    # 07.11: пунктуация ПЕРВАЯ — сжимает двойные пробелы и ставит
    # пропущенные; иначе «слово  -  слово» не дойдёт до правила тире
    seg = _punct(seg, counts)
    # «?...» -> «?..» ДО перевода точек в многоточие: иначе три точки
    # превратятся в «…» и вопрос потеряется
    seg, k = RE_DOTS_AFTER.subn(r"\1..", seg)
    counts["dots"] += k
    seg, k = RE_DOTS.subn("…", seg)
    counts["dots"] += k
    seg, k = RE_DASH_SP.subn(" — ", seg)
    counts["dash"] += k
    seg, k = RE_DASH_DB.subn(" — ", seg)
    counts["dash"] += k
    seg, k = RE_DASH_GAP.subn("— ", seg)
    counts["dash"] += k
    # 07.11: диапазоны — годы и en dash
    seg, k = RE_RANGE_YEARS.subn("—", seg)
    counts["dash"] += k
    seg, k = RE_RANGE_ENDASH.subn("—", seg)
    counts["dash"] += k
    if dialogue:
        seg, k = RE_DIALOG.subn(r"\1— ", seg)
        counts["dash"] += k
    seg, k = _quotes(seg)
    counts["quotes"] += k
    # 07.11: пробелы внутри кавычек — после всех преобразований кавычек
    seg, k = RE_Q_SPACE_OPEN.subn(r"\1", seg)
    counts["quotes"] += k
    seg, k = RE_Q_SPACE_CLOSE.subn(r"\1", seg)
    counts["quotes"] += k
    if nbsp:
        seg, k = _nbsp(seg)
        counts["nbsp"] += k
    return seg


def transform_text(text, nbsp=False, dialogue=False, frontmatter=False):
    """(новый_текст, счётчики по правилам). Блоки кода не трогаются.

    dialogue=True — конвертировать «- Реплика» в начале строки;
    frontmatter=True — пропустить yaml-блок "---...---" в начале файла."""
    counts = {k: 0 for k in RULE_KEYS}
    if not text:
        return text, counts
    lines = text.split("\n")
    out = []
    in_fence = False
    fence_marker = None
    in_fm = False
    for i, line in enumerate(lines):
        if frontmatter and i == 0 and line.strip() == "---":
            in_fm = True
            out.append(line)
            continue
        if in_fm:
            if line.strip() == "---":
                in_fm = False
            out.append(line)
            continue
        stripped = line.lstrip()
        if stripped.startswith(FENCE_RE):
            if not in_fence:
                in_fence, fence_marker = True, stripped[:3]
            elif stripped.startswith(fence_marker):
                in_fence, fence_marker = False, None
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        # inline-код `...`: правим только сегменты вне кода; при непарных
        # бэктиках сегментацию нельзя определить — кавычки/nbsp пропускаем
        if line.count("`") % 2 == 0:
            segs = line.split("`")
            for j in range(0, len(segs), 2):
                segs[j] = _apply_inline(segs[j], nbsp, dialogue, counts)
            line = "`".join(segs)
        else:
            line = _apply_inline(line, False, dialogue, counts)
        out.append(line)
    return "\n".join(out), counts


def collect(root):
    root = tp.check_root(root)  # 05.11: пустой/несуществующий --input — ошибка
    if root.is_file():
        return [root] if root.suffix.lower() in EXTS else []
    files = []
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in EXTS:
            continue
        if set(f.parts) & SKIP_DIRS or f.name.endswith(".bak"):
            continue
        files.append(f)
    return files


def _fmt_counts(counts):
    return ", ".join(f"{RULE_TITLES[k]} {counts[k]}"
                     for k in RULE_KEYS if counts[k]) or "нет правок"


# --- вычитка (--check): найти проблемы, файл не правится (07.11) ---

CHECK_PATTERNS = (
    ("прямые кавычки", re.compile(r'"')),
    ("ёлочки без пары", None),
    ("двойной пробел", RE_MULTI_SP),
    ("пробел перед знаком", RE_PUNCT_BEFORE),
    ("нет пробела после знака", re.compile(
        r"[,;](?=[А-Яа-яЁё«(])|[.!?…](?=\((?!\))|[А-ЯЁ«—])")),
    ("дефис вместо тире", re.compile(r"(?<=\S) - (?=\S)|(?<=\S)--(?=\S)")),
    ("многоточие из точек", re.compile(r"\.{3,}")),
    ("дефис в диапазоне лет", re.compile(r"\d{4}-\d{4}")),
    ("«?...» вместо «?..»", re.compile(r"[?!]\.{3,}")),
    ("пробел внутри кавычек", re.compile(
        r"(«|„) +(?=[^\s—–-])|(?<=[^\s—–-]) +(»|“)")),
)
CHECK_SHOW = 10          # первых находок на файл в консоли
CHECK_FRAG = 80          # длина фрагмента


def _check_line(text):
    """[(тип, фрагмент)] для одной строки. Сегменты вне inline-кода;
    при непарных бэктиках — вся строка."""
    if text.count("`") % 2 == 0:
        targets = text.split("`")[0::2]
    else:
        targets = [text]
    found = []
    seen = set()
    for seg in targets:
        for name, rx in CHECK_PATTERNS:
            if name in seen:
                continue
            if rx is None:  # ёлочки без пары
                if seg.count("«") != seg.count("»"):
                    seen.add(name)
                    found.append((name, seg.strip()[:CHECK_FRAG]))
                continue
            m = rx.search(seg)
            if m:
                seen.add(name)
                a = max(0, m.start() - 25)
                frag = seg[a:m.end() + 25].strip()[:CHECK_FRAG]
                found.append((name, frag))
    return found


def check_text(text):
    """[(строка, тип, фрагмент)] — вне код-блоков и frontmatter."""
    findings = []
    in_fence, fence_marker, in_fm = False, None, False
    for i, line in enumerate(text.split("\n"), 1):
        stripped = line.lstrip()
        if i == 1 and stripped == "---":
            in_fm = True
            continue
        if in_fm:
            if stripped == "---":
                in_fm = False
            continue
        if stripped.startswith(FENCE_RE):
            if not in_fence:
                in_fence, fence_marker = True, stripped[:3]
            elif stripped.startswith(fence_marker):
                in_fence, fence_marker = False, None
            continue
        if in_fence:
            continue
        for name, frag in _check_line(line):
            findings.append((i, name, frag))
    return findings


def check_docx(path):
    """[(абзац, тип, фрагмент)] по абзацам тела документа (читаемо).
    Таблицы и сноски вычитка не смотрит — только набор и правка."""
    try:
        from docx import Document
        doc = Document(path)
    except Exception as e:
        print(f"ПРОПУСК (docx не читается): {Path(path).name}: {e}")
        return None
    findings = []
    for i, p in enumerate(doc.paragraphs, 1):
        if not p.text.strip():
            continue
        for name, frag in _check_line(p.text):
            findings.append((i, name, frag))
    return findings


def run_check(input_path, out=None):
    """Режим вычитки: перечисляет проблемные места, файлы не меняются."""
    files = collect(input_path)
    if not files:
        print("Файлы .md/.txt/.docx не найдены.")
        return 1
    total = len(files)
    print(f"PROGRESS:0/{total}", flush=True)
    per_type = {name: 0 for name, _ in CHECK_PATTERNS}
    listings = []          # (файл, координата, [(строка, тип, фрагмент)])
    files_found = 0
    for idx, f in enumerate(files, 1):
        if tp.stop_requested():
            print("Остановлено пользователем.")
            break
        try:
            if f.suffix.lower() == ".docx":
                findings = check_docx(f)
                coord = "абзац {}"
            else:
                with open(f, "r", encoding="utf-8", newline="") as fh:
                    text = fh.read()
                if text.startswith("\ufeff"):
                    text = text[1:]
                findings = check_text(text)
                coord = "строка {}"
        except (UnicodeDecodeError, PermissionError, OSError) as e:
            print(f"ПРОПУСК {f.name}: {e}")
            print(f"PROGRESS:{idx}/{total}", flush=True)
            continue
        print(f"PROGRESS:{idx}/{total}", flush=True)
        if not findings:  # docx не читается — None, либо чисто
            continue
        files_found += 1
        entries = []
        for line_no, name, frag in findings:
            per_type[name] += 1
            entries.append((coord.format(line_no), name, frag))
        listings.append((f, entries))
        for co, name, frag in entries[:CHECK_SHOW]:
            print(f"{f.name}:{co}: {name} — {frag}")
        if len(entries) > CHECK_SHOW:
            print(f"  ... ещё {len(entries) - CHECK_SHOW} в {f.name}")
    grand = sum(per_type.values())
    print(f"\nИтого: проблем {grand} в {files_found} файлах.")
    for name, _ in CHECK_PATTERNS:
        if per_type[name]:
            print(f"  {name}: {per_type[name]}")
    print("Режим вычитки — файлы НЕ изменены. Правка: тот же инструмент "
          "с галочкой «Применить» (--fix).")
    if out:
        lines = [f"# Вычитка — {input_path}",
                 "Режим: только поиск, файлы не изменены.", "",
                 "| Тип проблемы | Найдено |", "|---|---:|"]
        for name, _ in CHECK_PATTERNS:
            if per_type[name]:
                lines.append(f"| {name} | {per_type[name]} |")
        if grand:
            lines += ["", f"**Итого:** проблем {grand} в {files_found} файлах."]
        for f, entries in listings:
            lines += ["", f"## {f}"]
            for co, name, frag in entries:
                frag = frag.replace("|", "\\|")
                lines.append(f"- {co}: {name} — {frag}")
        write_report(out, "\n".join(lines))
    return 0


def run(input_path, fix=False, nbsp=False, out=None, check=False):
    # 07.11: вычитка — самостоятельный режим, правит файлы --fix
    if check:
        return run_check(input_path, out=out)
    files = collect(input_path)
    if not files:
        print("Файлы .md/.txt/.docx не найдены.")
        return 1
    total_files = 0
    totals = {k: 0 for k in RULE_KEYS}
    rows = []
    total = len(files)
    print(f"PROGRESS:0/{total}", flush=True)
    for idx, f in enumerate(files, 1):
        if tp.stop_requested():
            print("Остановлено пользователем.")
            break
        try:
            counts = None
            if f.suffix.lower() == ".docx":
                counts = fix_docx(f, nbsp, fix)
            else:
                # 04.11: чтение и запись с newline="" — переводы строк
                # файла не меняются; BOM сохраняется, иначе «\ufeff---»
                # не распознавался как frontmatter и типографика
                # портила YAML (--  ->  —)
                with open(f, "r", encoding="utf-8", newline="") as fh:
                    text = fh.read()
                had_bom = text.startswith("\ufeff")
                if had_bom:
                    text = text[1:]
                new_text, counts = transform_text(
                    text, nbsp=nbsp,
                    dialogue=f.suffix.lower() != ".md", frontmatter=True)
                if sum(counts.values()) and fix:
                    tp.backup_once(f)  # 20.10: старый .bak не затирается
                    with open(f, "w",
                              encoding="utf-8-sig" if had_bom else "utf-8",
                              newline="") as fh:
                        fh.write(new_text)
        except (UnicodeDecodeError, PermissionError, OSError) as e:
            print(f"ПРОПУСК {f.name}: {e}")
            print(f"PROGRESS:{idx}/{total}", flush=True)
            continue
        print(f"PROGRESS:{idx}/{total}", flush=True)
        if sum(counts.values()):
            total_files += 1
            for k in RULE_KEYS:
                totals[k] += counts[k]
            rows.append((str(f), counts))
            print(f"{'[FIX] ' if fix else ''}{f}: {_fmt_counts(counts)}")
    grand = sum(totals.values())
    print(f"\nИтого: файлов с правками {total_files}, правок {grand} "
          f"({_fmt_counts(totals)})")
    if not fix and grand:
        print("Режим dry-run — файлы НЕ изменены. Для правки: --fix")
    if not nbsp:
        print("Неразрывные пробелы выключены (--nbsp)")
    if out:
        lines = [f"# Типографика — {input_path}",
                 f"Режим: {'ПРИМЕНЕНО (--fix)' if fix else 'dry-run (файлы не изменены)'}",
                 "",
                 "| Файл | многоточия | тире и диапазоны | «ёлочки» | "
                 "пунктуация | неразрывные | Всего |",
                 "|---|---:|---:|---:|---:|---:|---:|"]
        for path, c in rows:
            lines.append("| {} | {} | {} | {} | {} | {} | {} |".format(
                path, c["dots"], c["dash"], c["quotes"], c["punct"],
                c["nbsp"], sum(c.values())))
        lines += ["",
                  f"**Итого:** файлов с правками {total_files}, правок {grand}.",
                  f"Неразрывные пробелы: {'включены' if nbsp else 'выключены (--nbsp)'}."]
        write_report(out, "\n".join(lines))
    return 0


# --- docx ---

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DOC_PART_KEYWORDS = (
    "document.xml", "header", "footer", "footnotes", "endnotes", "comments")


def fix_docx(path, nbsp, fix):
    """Типографика docx: только текст w:t (тело, сноски, колонтитулы).
    Форматирование сохраняется. Кавычки конвертируются в пределах одного
    w:t — разорванные форматированием кавычки не трогаются (безопаснее)."""
    try:
        # 04.11: импорт внутри try — без python-docx будет ПРОПУСК,
        # а не трейсбек посреди прогона
        from docx import Document
        doc = Document(path)
    except Exception as e:
        print(f"ПРОПУСК (docx не читается): {Path(path).name}: {e}")
        return {k: 0 for k in RULE_KEYS}

    counts = {k: 0 for k in RULE_KEYS}
    for part in doc.part.package.iter_parts():
        name = str(part.partname)
        if "/word/" not in name or not any(k in name for k in DOC_PART_KEYWORDS):
            continue
        el = getattr(part, "_element", None)
        if el is None:
            continue
        for t_el in el.iter(W_NS + "t"):
            txt = t_el.text
            if not txt:
                continue
            new, c = transform_text(txt, nbsp=nbsp, dialogue=True)
            if sum(c.values()):
                t_el.text = new
                if new != new.strip():
                    t_el.set(
                        "{http://www.w3.org/XML/1998/namespace}space",
                        "preserve")
                for k in RULE_KEYS:
                    counts[k] += c[k]
    if sum(counts.values()) and fix:
        tp.backup_once(path)  # 20.10: старый .bak не затирается
        try:
            doc.save(path)
        except Exception as e:
            print(f"ПРОПУСК (не сохраняется, файл занят?): {Path(path).name}: {e}")
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser(description="Приведение типографики к русской норме")
    ap.add_argument("--input", required=True, help="папка или файл .md/.txt/.docx")
    ap.add_argument("--fix", action="store_true", help="реально править (с .bak)")
    ap.add_argument("--nbsp", action="store_true",
                    help="неразрывные пробелы: предлоги, инициалы, "
                         "«т. д.», число + слово")
    ap.add_argument("--check", action="store_true",
                    help="вычитка: только перечислить проблемные места, "
                         "файлы не правятся")
    ap.add_argument("--out", help="файл отчёта")
    args = ap.parse_args(argv)
    if args.check and args.fix:
        print("--check — режим вычитки, файлы не правятся: --fix игнорируется.")
    return run(args.input, fix=args.fix, nbsp=args.nbsp, out=args.out,
               check=args.check)


if __name__ == "__main__":
    sys.exit(main())
