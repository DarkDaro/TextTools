# -*- coding: utf-8 -*-
"""
phrase_check — поиск фраз-паттернов и штампов ИИ-текста (22.09, волна 3).

Ищет точные фразы из пополняемого словаря в текстах .md/.txt/.docx:
  - встроенный список штампов ИИ-текста (нейросетевые обороты)
  - настраиваемый словарь phrases.yaml (рядом со скриптом)
  - собственные фразы через --phrase "текст" (можно несколько)

Использование:
  python phrase_check.py --input <папка/файл>              — отчёт
  python phrase_check.py --input <...> --custom <словарь>   — свой словарь
  python phrase_check.py --input <...> --phrase "текст"     — свои фразы
  python phrase_check.py --add "новая фраза"               — добавить в словарь
"""
import argparse
import sys
from pathlib import Path
# 26.10: Counter не используется (мёртвый импорт) — отключён
# from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.report import write_report
# 26.10: read_text не используется (читаем через docx_io ниже) — отключён
# from core.text_parser import iter_text_files, read_text, norm_yo
from core.text_parser import iter_text_files, norm_yo

# --- Встроенный словарь штампов ИИ-текста --------------------------------

BUILTIN_PHRASES = [
    # Нейросетевые обороты-связки
    "стоит отметить, что",
    "важно отметить, что",
    "необходимо отметить",
    "следует отметить",
    "в заключение стоит сказать",
    "подводя итог",
    "таким образом,",
    "в конечном итоге",
    "в целом, можно сказать",
    "с одной стороны",
    "с другой стороны",
    "тем не менее,",
    "однако, важно понимать",
    "не секрет, что",
    "давайте рассмотрим",
    "давайте разберёмся",
    "перейдём к следующему",
    # Штампы описаний
    "особое внимание",
    "играет важную роль",
    "играет ключевую роль",
    "в современном мире",
    "в наше время",
    "на сегодняшний день",
    "по сей день",
    "в последние годы",
    "все чаще и чаще",
    "широко распространено",
    "с каждым днем",
    # Канцелярит (22.09: расширен по запросу пользователя)
    "в рамках данного",
    "в рамках реализации",
    "в целях повышения",
    "в соответствии с требованиями",
    "в связи с вышеизложенным",
    "осуществляет деятельность",
    "осуществление деятельности",
    "имеет место быть",
    "данный метод позволяет",
    "данный подход позволяет",
    "данный вопрос требует",
    "в процессе работы над данным",
    "комплексный подход",
    "эффективное решение",
    "инновационные технологии",
    "оптимизация процессов",
    "выполнение поставленных задач",
    "реализация поставленных задач",
    "представляет собой",
    "в случае возникновения",
    "при необходимости можно",
    "является целесообразным",
    "целесообразно рассмотреть",
    "необходимо провести",
    "существует необходимость",
    "имеет большое значение",
    "имеет огромное значение",
    "не вызывает сомнений",
    "трудно переоценить",
    "как известно,",
    "известно, что",
]

PHRASES_FILE = Path(__file__).parent / "phrases.yaml"


def load_phrases(custom_path=None):
    """Встроенный список + файл пользователя (если есть)."""
    phrases = list(BUILTIN_PHRASES)
    if custom_path and Path(custom_path).exists():
        import yaml
        with open(custom_path, encoding="utf-8") as fh:
            extra = yaml.safe_load(fh) or []
        # 04.11: файл-словарь вместо списка раньше молча давал мусор
        if not isinstance(extra, list):
            print(f"ПРЕДУПРЕЖДЕНИЕ: {custom_path}: ожидался список строк — "
                  "файл пропущен.")
            extra = []
        phrases.extend(str(p).lower() for p in extra)
    return phrases


def add_phrase(phrase):
    """Добавить фразу в пользовательский словарь (phrases.yaml)."""
    import yaml
    phrase = phrase.strip().lower()
    if not phrase:
        print("Пустая фраза.")
        return
    current = []
    if PHRASES_FILE.exists():
        with open(PHRASES_FILE, encoding="utf-8") as fh:
            current = yaml.safe_load(fh) or []
        if not isinstance(current, list):
            print(f"{PHRASES_FILE.name}: ожидался список строк — файл "
                  "не тронут.")
            return
    if phrase in current:
        print(f"Уже есть: {phrase}")
        return
    current.append(phrase)
    with open(PHRASES_FILE, "w", encoding="utf-8") as fh:
        yaml.dump(current, fh, allow_unicode=True, sort_keys=False)
    print(f"Добавлено: {phrase} (всего в словаре: {len(current) + len(BUILTIN_PHRASES)})")


def count_phrase(text, phrase):
    """Число вхождений фразы в текст (регистронезависимо, ё=е, 01.10)."""
    return norm_yo(text.lower()).count(norm_yo(phrase))


def run(input_path, custom=None, phrases=None, limit=None, out=None):
    # Собираем список поиска
    search = load_phrases_list(custom, phrases)

    # 22.09: два прохода — сначала считаем файлы (для прогресса),
    # потом сканируем с печатью PROGRESS:N/M (GUI ловит и красит бар)
    files = list(iter_text_files(input_path, limit=limit))
    total = len(files)
    print(f"PROGRESS:0/{total}", flush=True)

    total_hits = {}
    n_files = 0
    for f in files:
        if stop_requested():
            print("Остановлено пользователем.")
            break
        n_files += 1
        try:
            content = read_file(f)
        except Exception:
            content = None
        if content:
            low = norm_yo(content.lower())  # 01.10: ё=е
            for ph in search:
                c = low.count(norm_yo(ph))
                if c:
                    total_hits.setdefault(ph, []).append((str(f), c))
        if n_files % 10 == 0 or n_files == total:
            print(f"PROGRESS:{n_files}/{total}", flush=True)

    # Отчёт
    print(f"Файлов проверено: {n_files}")
    print(f"Фраз в словаре: {len(search)}")
    if not total_hits:
        print("\nШтампов не найдено — текст чистый.")
        return 0

    # Сортировка по общему числу вхождений
    rows = sorted(total_hits.items(),
                  key=lambda kv: sum(c for _, c in kv[1]), reverse=True)
    total_count = sum(c for ph, lst in rows for _, c in lst)
    print(f"\nНайдено штампов: {len(rows)} видов, {total_count} вхождений")
    for ph, lst in rows[:15]:
        s = sum(c for _, c in lst)
        files = sorted({f for f, _ in lst})
        print(f"  {ph!r}: {s} вхождений, {len(files)} файлов")
        for f in files[:2]:
            print(f"      {f}")
        if len(files) > 2:
            print(f"      ... ещё {len(files) - 2}")

    if out:
        lines = ["# Phrase check — штампы и шаблонные фразы", "",
                 f"Папка: {input_path}", f"Файлов: {n_files}",
                 f"Видов штампов: {len(rows)}, вхождений: {total_count}", ""]
        for ph, lst in rows:
            s = sum(c for _, c in lst)
            lines.append(f"## {ph} ({s})")
            for f, c in sorted(lst):
                lines.append(f"- {f}: {c}")
            lines.append("")
        write_report(out, "\n".join(lines))
        print(f"\nОтчёт: {out}")
    return 0


def load_phrases_list(custom=None, extra=None):
    """Встроенный + YAML-словарь + фразы из CLI."""
    result = load_phrases(custom)
    result.extend(p.strip().lower() for p in (extra or []) if p.strip())
    return result


def read_file(f):
    """Чтение файла любого из 3 форматов (docx через docx_io).
    04.11: с newline="" — переводы строк сохраняются как есть,
    CRLF-файл при записи не превращается в LF и наоборот."""
    if f.suffix.lower() == ".docx":
        from core import docx_io
        t = docx_io.read_text(f)
        return t or ""
    with open(f, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def _replace_preserving_case(text, phrase, repl):
    """Замена с сохранением регистра первой буквы оригинала.

    04.11: правки локальны — убраны глобальные схлопывание двойных
    пробелов и срез ведущих пробелов строк, которые ломали
    markdown-переносы (2 пробела в конце строки) и отступы
    код-блоков и вложенных списков во всём файле. Пробелы правятся
    только на стыках с удалённой фразой; пробелы перед переводом
    строки не трогаются."""
    if not phrase:
        return text
    # 01.10: ё=е; norm_yo не меняет длину — индексы валидны в оригинале
    low = norm_yo(text.lower())
    ph_low = norm_yo(phrase.lower())
    out = []
    pos = 0
    n = len(text)
    while True:
        i = low.find(ph_low, pos)
        if i < 0:
            out.append(text[pos:])
            break
        out.append(text[pos:i])
        # регистр: смотрим последний непробельный символ перед фразой
        j = i - 1
        while j >= 0 and text[j] in " \t":
            j -= 1
        at_sentence_start = (i == 0) or (j >= 0 and text[j] in ".!?\n\r")
        repl_cased = repl[:1].upper() + repl[1:] \
            if (repl and at_sentence_start) else repl
        if repl_cased:
            out.append(repl_cased)
            pos = i + len(ph_low)
        else:
            # удаление связки: пробелы правятся только на стыках.
            # Раньше (до 04.11) после удаления глобально схлопывались
            # все двойные пробелы файла и срезались отступы строк
            if out:
                out[-1] = out[-1].rstrip(" \t")
            pos = i + len(ph_low)
            # пробелы после фразы: смотрим, кончаются ли они переводом
            # строки — хвостовые два пробела это markdown-перенос
            k = pos
            while k < n and text[k] in " \t":
                k += 1
            tail_inner = k < n and text[k] not in "\r\n"
            head_inner = bool(out) and out[-1] != "" \
                and out[-1][-1] not in "\r\n"
            # стык в середине строки оставляем с одним пробелом,
            # на краях строки пробелы не добавляем
            if head_inner and tail_inner:
                out.append(" ")
            if tail_inner:
                pos = k
    return "".join(out)


def write_file(f, content):
    """Запись .md/.txt. 04.11: с newline="" — переводы строк файла
    не меняются. Docx в чистке идёт через _clean_docx_phrases —
    пофразовая замена с сохранением форматирования (прежняя перезапись
    всего текста задваивала таблицы и колонтитулы)."""
    with open(f, "w", encoding="utf-8", newline="") as fh:
        fh.write(content)


def _clean_docx_phrases(f, phrases):
    """Пофразовая замена в docx (тело, таблицы, колонтитулы, сноски)
    с сохранением форматирования run'ов. Возвращает число замен."""
    from core import docx_io
    total = 0
    for ph, repl in phrases:
        n, _changed, _broken = docx_io.replace_in_docx(f, ph, repl,
                                                       backup=False)
        total += n
    return total


# --- Очистка штампов (22.09) ----------------------------------------------

# Словарь замен по умолчанию: штамп -> чем заменить
# (пустая строка = просто удалить связку)
DEFAULT_CLEAN_MAP = {
    "стоит отметить, что": "",
    "важно отметить, что": "",
    "необходимо отметить, что": "",
    "следует отметить, что": "",
    "нужно отметить, что": "",
    "стоит отметить,": "",
    "важно отметить,": "",
    "в заключение стоит сказать, что": "",
    "подводя итог,": "",
    "таким образом,": "",
    "в конечном итоге": "в итоге",
    "в современном мире": "сегодня",
    "в наше время": "сегодня",
    "на сегодняшний день": "сегодня",
    "с каждым днем": "всё чаще",
    "все чаще и чаще": "всё чаще",
    "имеет большое значение": "важно",
    "имеет огромное значение": "крайне важно",
    "не вызывает сомнений": "очевидно",
    "трудно переоценить": "крайне важно",
    "как известно,": "",
    "известно, что": "",
    "играет важную роль в": "важен для",
    "играет ключевую роль в": "определяет",
    "не секрет, что": "",
    "давайте рассмотрим": "рассмотрим",
    "давайте разберёмся": "разберёмся",
    "перейдём к следующему": "далее",
    "с одной стороны": "",
    "с другой стороны": "зато",
    "тем не менее,": "однако",
    "в целом, можно сказать, что": "",
    "можно с уверенностью сказать, что": "",
}

CLEAN_MAP_FILE = Path(__file__).parent / "phrases_clean.yaml"


def load_clean_map():
    """Словарь очистки: встроенный + пользовательский (если есть)."""
    mapping = dict(DEFAULT_CLEAN_MAP)
    if CLEAN_MAP_FILE.exists():
        import yaml
        extra = yaml.safe_load(open(CLEAN_MAP_FILE, encoding="utf-8")) or {}
        mapping.update({str(k).lower(): v for k, v in extra.items()})
    return mapping


# --- Витрина чистки (01.10): контекст каждого вхождения + выборочное
#     применение из GUI -----------------------------------------------

def review(input_path, clean_map_path=None, limit=None):
    """Печатает каждое вхождение штампа с контекстом строками:
    REVIEW\tфраза\tзамена\tфайл\tстрока\tфрагмент. GUI строит по ним
    диалог выбора. Файлы не изменяются."""
    mapping = dict(DEFAULT_CLEAN_MAP)
    if clean_map_path and Path(clean_map_path).exists():
        import yaml
        extra = yaml.safe_load(open(clean_map_path, encoding="utf-8")) or {}
        mapping.update({str(k).lower(): v for k, v in extra.items()})
    items = sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True)

    files = list(iter_text_files(input_path, limit=limit))
    total = len(files)
    print(f"PROGRESS:0/{total}", flush=True)
    n_files = 0
    n_hits = 0
    for f in files:
        n_files += 1
        if stop_requested():
            print("Остановлено пользователем.")
            break
        try:
            content = read_file(f)
        except Exception:
            content = None
        if content:
            lines = content.splitlines()
            for ph, repl in items:
                # 20.10: ё=е и в витрине — вхождения с «ё» не теряются
                ph_low = norm_yo(ph.lower())
                for i, ln in enumerate(lines, 1):
                    low = norm_yo(ln.lower())
                    start = 0
                    while True:
                        j = low.find(ph_low, start)
                        if j < 0:
                            break
                        frag = ln[max(0, j - 30):j + len(ph) + 30].strip()
                        print(f"REVIEW\t{ph}\t{repl}\t{f}\t{i}\t{frag}",
                              flush=True)
                        n_hits += 1
                        start = j + len(ph)
        print(f"PROGRESS:{n_files}/{total}", flush=True)
    print(f"REVIEW-END\t{n_hits}", flush=True)
    return 0


def clean_selection(pairs, clean_map_path=None):
    """Чистит только выбранные вхождения.
    pairs: [(фраза, файл, строка)] — строка приходит из витрины (номер
    строки текста, 1-базовый). 04.11: раньше витрина передавала только
    (фраза, файл), и заменялись ВСЕ вхождения фразы в файле, а не
    отмеченные. Для .docx строки текста не соответствуют строкам
    документа — замена идёт пофразово во всём документе.
    С бэкапом в md_replace_backups. Возвращает строки-результаты."""
    mapping = dict(DEFAULT_CLEAN_MAP)
    if clean_map_path and Path(clean_map_path).exists():
        import yaml
        with open(clean_map_path, encoding="utf-8") as fh:
            extra = yaml.safe_load(fh) or {}
        mapping.update({str(k).lower(): v for k, v in extra.items()})

    by_file = {}
    for ph, fstr, ln in pairs:
        try:
            ln_no = int(ln)
        except (TypeError, ValueError):
            ln_no = 0
        by_file.setdefault(fstr, set()).add((ph.lower(), ln_no))

    results = []
    n_files = n_repl = 0
    import shutil
    import time as _t
    for fstr, wanted in by_file.items():
        f = Path(fstr)
        if f.suffix.lower() == ".docx":
            # строки текста docx не соответствуют строкам документа
            from core import docx_io
            low_text = norm_yo((docx_io.read_text(f) or "").lower())
            present = [(ph, mapping.get(ph, ""))
                       for ph, _ln in sorted(wanted, key=lambda t: -len(t[0]))
                       if norm_yo(ph) in low_text]
            if not present:
                continue
            bak_dir = f.parent / "md_replace_backups" / \
                _t.strftime("%Y-%m-%d_%H-%M-%S")
            bak_dir.mkdir(parents=True, exist_ok=True)
            bak = bak_dir / f.name
            if not bak.exists():
                shutil.copy2(f, bak)
            n = _clean_docx_phrases(f, present)
            if n:
                n_files += 1
                n_repl += n
                results.append(f"[ОЧИЩЕН] {f}: {n} правок")
            continue
        try:
            content = read_file(f)
        except (PermissionError, OSError, UnicodeDecodeError):
            continue
        lines = content.split("\n")
        # выбранные вхождения: (фраза, строка); длинные фразы первыми,
        # чтобы короткая не съела часть длинной
        present = sorted(
            ((ph, ln) for ph, ln in wanted
             if 1 <= ln <= len(lines)
             # 20.10: ё=е при поиске вхождений
             and norm_yo(ph) in norm_yo(lines[ln - 1].lower())),
            key=lambda t: -len(t[0]))
        if not present:
            continue
        n_repl_file = 0
        for ph, ln in present:
            idx = ln - 1
            old_line = lines[idx]
            repl = mapping.get(ph, "")
            lines[idx] = _replace_preserving_case(old_line, ph, repl)
            # фактическое число правок в этой строке (до замены)
            n_repl_file += norm_yo(old_line.lower()).count(norm_yo(ph))
        new = "\n".join(lines)
        if new != content:
            bak_dir = f.parent / "md_replace_backups" / \
                _t.strftime("%Y-%m-%d_%H-%M-%S")
            bak_dir.mkdir(parents=True, exist_ok=True)
            bak = bak_dir / f.name
            if not bak.exists():
                shutil.copy2(f, bak)
            write_file(f, new)
            n_files += 1
            n_repl += n_repl_file
            results.append(f"[ОЧИЩЕН] {f}: {n_repl_file} правок")
    results.append(f"Итого: файлов {n_files}, замен {n_repl}")
    return results


def stop_requested():
    from core.text_parser import stop_requested as _s
    return _s()


def clean(input_path, clean_map_path=None, limit=None, dry_run=True,
          yes=False, no_backup=False):
    """Чистка штампов по словарю замен. dry_run — только план."""
    import shutil
    import time as _t
    mapping = dict(DEFAULT_CLEAN_MAP)
    if clean_map_path and Path(clean_map_path).exists():
        import yaml
        extra = yaml.safe_load(open(clean_map_path, encoding="utf-8")) or {}
        mapping.update({str(k).lower(): v for k, v in extra.items()})
    if not mapping:
        print("Словарь очистки пуст.")
        return 1

    # 22.09: длинные фразы ПЕРВЫМИ (чтобы «стоит отметить, что» не съелось
    # коротким «стоит отметить»)
    items = sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True)

    files = list(iter_text_files(input_path, limit=limit))
    total = len(files)
    print(f"PROGRESS:0/{total}", flush=True)
    print(f"РЕЖИМ: {'DRY-RUN (файлы не изменены)' if dry_run else 'РЕАЛЬНАЯ ЗАМЕНА'}")
    print(f"Фраз в словаре очистки: {len(mapping)}")
    print()

    n_files = 0
    n_changed = 0
    n_replacements = 0
    plan = {}  # фраза -> [(файл, кол-во)]
    for f in files:
        if stop_requested():
            print("Остановлено пользователем.")
            break
        n_files += 1
        try:
            content = read_file(f)
        except Exception:
            content = None
        if not content:
            if n_files % 10 == 0 or n_files == total:
                print(f"PROGRESS:{n_files}/{total}", flush=True)
            continue
        low = norm_yo(content.lower())  # 01.10: ё=е
        file_hits = []
        for ph, repl in items:
            c = low.count(norm_yo(ph))
            if c:
                file_hits.append((ph, repl, c))
                plan.setdefault(ph, []).append((str(f), c))
        if file_hits and not dry_run:
            if f.suffix.lower() == ".docx":
                # 04.11: docx — пофразовая замена с сохранением
                # форматирования; перезапись всего текста задваивала
                # таблицы и колонтитулы
                if not no_backup:
                    bak_dir = Path(f).parent / "md_replace_backups" / \
                        _t.strftime("%Y-%m-%d_%H-%M-%S")
                    bak_dir.mkdir(parents=True, exist_ok=True)
                    bak = bak_dir / f.name
                    if not bak.exists():
                        shutil.copy2(f, bak)
                n_docx = _clean_docx_phrases(
                    f, [(ph, repl) for ph, repl, _ in file_hits])
                if n_docx:
                    n_changed += 1
                    n_replacements += n_docx
                    print(f"  [ОЧИЩЕН] {f}: {n_docx} правок")
            else:
                # замены: идём по убыванию длины, регистр оригинала теряем
                # у заглавной первой буквы (фразы все в нижнем регистре)
                new = content
                for ph, repl, _ in file_hits:
                    new = _replace_preserving_case(new, ph, repl)
                if new != content:
                    if not no_backup:
                        bak_dir = Path(f).parent / "md_replace_backups" / \
                            _t.strftime("%Y-%m-%d_%H-%M-%S")
                        # 20.10: одиночный файл — бэкап по имени; rel с
                        # абсолютным путём делал bak самим файлом
                        rel = f.relative_to(Path(input_path)) \
                            if not Path(input_path).is_file() else f.name
                        bak = bak_dir / rel
                        bak.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, bak)
                    write_file(f, new)
                    n_changed += 1
                    n_replacements += sum(c for _, _, c in file_hits)
                    print(f"  [ОЧИЩЕН] {f}: {sum(c for _, _, c in file_hits)} правок")
        if n_files % 10 == 0 or n_files == total:
            print(f"PROGRESS:{n_files}/{total}", flush=True)

    # Отчёт
    total_count = sum(c for lst in plan.values() for _, c in lst)
    if not plan:
        print("\nШтампов не найдено — чистить нечего.")
        return 0
    print(f"\nВидов штампов: {len(plan)}, вхождений: {total_count}")
    if dry_run:
        print("\nПлан замен (что будет сделано при «Почистить»):")
        rows = sorted(plan.items(), key=lambda kv: sum(c for _, c in kv[1]),
                      reverse=True)
        for ph, lst in rows[:20]:
            s = sum(c for _, c in lst)
            repl = mapping.get(ph, "")
            action = f"-> {repl!r}" if repl else "-> удалить"
            print(f"  {ph!r} ({s}x) {action}")
    if dry_run:
        print("\nDRY-RUN — файлы не изменены. Снимите галочку «Только отчёт» для чистки.")
    else:
        print(f"\nИзменено файлов: {n_changed}, замен: {n_replacements}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Поиск и чистка фраз-штампов ИИ")
    ap.add_argument("--input", required=False, default=None, help="папка или файл")
    ap.add_argument("--custom", help="свой YAML-словарь фраз (список строк)")
    ap.add_argument("--phrase", action="append", default=[],
                    help="своя фраза для поиска (можно несколько раз)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", help="записать отчёт в файл .md")
    ap.add_argument("--add", help="добавить фразу в постоянный словарь и выйти")
    # 22.09: очистка
    ap.add_argument("--clean", action="store_true",
                    help="режим очистки штампов по словарю замен")
    ap.add_argument("--review", action="store_true",
                    help="витрина: каждое вхождение с контекстом (REVIEW-строки)")
    ap.add_argument("--clean-map", help="свой YAML-словарь (фраза: замена)")
    ap.add_argument("--dry-run", action="store_true",
                    help="очистка: только показать план")
    ap.add_argument("--yes", "-y", action="store_true", help="без подтверждения")
    ap.add_argument("--no-backup", action="store_true", help="не делать бэкапы")
    args = ap.parse_args(argv)

    if args.add:
        add_phrase(args.add)
        return 0

    if not args.input:
        ap.error("--input обязателен (кроме --add)")
        return 1

    if args.review:
        return review(args.input, clean_map_path=args.clean_map,
                      limit=args.limit)

    if args.clean:
        return clean(args.input, clean_map_path=args.clean_map,
                     limit=args.limit, dry_run=args.dry_run or not args.yes,
                     yes=args.yes, no_backup=args.no_backup)

    return run(args.input, custom=args.custom, phrases=args.phrase,
               limit=args.limit, out=args.out)


if __name__ == "__main__":
    sys.exit(main())
