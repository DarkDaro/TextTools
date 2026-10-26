# -*- coding: utf-8 -*-
"""
textools tools: yo_audit — ё/е-аудит текста (20.10).

Русская ё капризна: по норме её можно опускать повсеместно, но в прозе
это создаёт скрытые проблемы: имени собственные (Семён/Семен), пары слов,
где е/ё меняет смысл (все/всё, небо/нёбо). Инструмент показывает эти места
с контекстом; замена — только по выбранному в диалоге-витрине.

Три категории:
  имена        — несовпадение с реестром персонажей (текст должен быть
                 написан так, как в реестре);
  омографы     — смысл зависит от написания (все/всё и т.п.); витрина
                 показывает оба написания, решение по контексту;
  словарные    — в проекте принято написание с ё (словарь пар), но в
                 тексте встречается е-вариант.

Словарь: tools/yo_dict.yaml; если файл существует, он полностью заменяет
встроенный список (как parasites.yaml). Формат:

  омографы:      # смысл зависит от написания
    - все|всё
    - небо|нёбо
  словарные:     # в проекте принят правый вариант
    - объем|объём
    - черный|чёрный

CLI:
  py tools/yo_audit.py --input папка [--registry реестр.yaml] [--review] [--out отчёт.md]
"""
import argparse
import re
import shutil
import sys
import time as _t
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import name_registry as nr
# 26.10: tp не используется (мёртвый импорт) — отключён
# from core import text_parser as tp

SKIP_DIRS = {".git", ".obsidian", ".trash", "reports", "__pycache__",
             "md_replace_backups", ".smart-env"}
EXTS = (".md", ".txt", ".docx")
FRAG_LEN = 70

DICT_FILE = Path(__file__).parent / "yo_dict.yaml"

BUILTIN = {
    # смысл зависит от написания: только витрина, решение по контексту
    "омографы": [
        ("все", "всё"),
        ("мел", "мёл"),          # мел (порошок) vs мёл (месить)
        ("небо", "нёбо"),
        ("ведро", "вёдро"),
        ("падеж", "падёж"),
    ],
    # в проекте принят вариант с ё (обычная практика прозы)
    "словарные": [
        ("черный", "чёрный"), ("желтый", "жёлтый"),
        ("зеленый", "зелёный"), ("легкий", "лёгкий"),
        ("жесткий", "жёсткий"), ("шепот", "шёпот"),
        ("объем", "объём"), ("желоб", "жёлоб"),
        ("шел", "шёл"),
    ],
}


def _norm_pair(entry):
    """'е|ё' -> (е, ё). Некорректные строки возвращают None."""
    parts = [p.strip() for p in str(entry).split("|")]
    if len(parts) == 2 and all(parts):
        return parts[0], parts[1]
    return None


def load_dict(dict_path=None):
    """Встроенный словарь; yo_dict.yaml (или заданный) его заменяет
    полностью. Возвращает {категория: [(е-слово, ё-слово)]}."""
    path = Path(dict_path) if dict_path else DICT_FILE
    d = {k: list(v) for k, v in BUILTIN.items()}
    if path.exists():
        try:
            import yaml
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for cat in d:
                vals = [p for p in (_norm_pair(x) for x in (data.get(cat) or []))
                        if p]
                if vals:
                    d[cat] = vals
        except Exception as e:
            print(f"Словарь не прочитан ({path.name}): {e} — использую "
                  f"встроенный.")
    return d


def name_pairs(chars):
    """Пары имён: реестр пишет с ё, е-вопрос — ошибка переноса формы.
    [(е-вариант, форма-из-реестра)]."""
    pairs = []
    seen = set()
    for c in chars:
        forms = [c["имя"]] + list(c.get("формы") or [])
        for f in forms:
            if not f or "ё" not in f.lower():
                continue
            alt = f.replace("ё", "е").replace("Ё", "Е")
            key = alt.lower()
            if key in seen:
                continue
            seen.add(key)
            pairs.append((alt, f))
    return pairs


def _word_pattern(w):
    """Границы слова: ё/е должны совпадать ЛИТЕРАЛЬНО (е-написание и
    ё-написание ищутся отдельно, это и есть суть аудита). Тире внутри
    допустимо («Анна-Мария», «всё-таки»). (?i:...) — регистр не важен."""
    esc = re.escape(w)
    return re.compile(r"(?<![\wёЁ])" + "(?i:" + esc + ")" + r"(?![\wёЁ])")


def _frag(line, start, end):
    s = max(0, start - 30)
    e = min(len(line), end + 30)
    prefix = "…" if s > 0 else ""
    return prefix + line[s:e].strip()[:FRAG_LEN]


def scan(input_path, targets, stats):
    """Один файл: [(wrong, right, файл, строка, фрагмент)].
    targets: [(wrong, right, категория)]."""
    from core import docx_io
    f = Path(input_path)
    try:
        if f.suffix.lower() == ".docx":
            content = docx_io.read_text(f) or ""
        else:
            content = f.read_text(encoding="utf-8", errors="replace")
    except (PermissionError, OSError, UnicodeDecodeError) as e:
        print(f"ПРОПУСК {f.name}: {e}")
        return []
    if not content:
        return []
    if content.startswith("\ufeff"):
        content = content[1:]  # BOM не нужен ни в тексте, ни во фрагменте
    stats["ё_всего"] += content.count("ё") + content.count("Ё")

    hits = []
    lines = content.splitlines()
    for wrong, right, cat in targets:
        rx = _word_pattern(wrong)
        for i, ln in enumerate(lines, 1):
            for m in rx.finditer(ln):
                hits.append((m.group(0), right, str(f), str(i),
                             _frag(ln, m.start(), m.end())))
                key = f"{cat}|{wrong}|{right}"
                stats.setdefault(key, 0)
                stats[key] += 1
    return hits


def yowords_all(dictionary, name_p):
    """Все цели [(wrong, right, категория)]: словарь + реестр (без дублей)."""
    targets = []
    for cat, vals in dictionary.items():
        for еv, ёv in vals:
            targets.append((еv, ёv, cat))
            # обратное направление: в тексте может стоять «лишняя» ё
            if еv != ёv:
                targets.append((ёv, еv, cat))
    seen = set()
    result = []
    for w, r, c in targets:
        if w.lower() in seen:
            continue
        seen.add(w.lower())
        result.append((w, r, c))
    for alt, right in name_p:
        if alt.lower() not in seen:
            seen.add(alt.lower())
            result.append((alt, right, "имена"))
    return result


def iter_text_files(root, limit=None):
    root = Path(root)
    if root.is_file():
        yield root
        return
    files = [f for f in sorted(root.rglob("*"))
             if f.is_file() and f.suffix.lower() in EXTS
             and not (set(f.parts) & SKIP_DIRS)
             and not f.name.endswith(".bak")]
    if limit:
        files = files[:limit]
    yield from files


def stop_requested():
    from core.text_parser import stop_requested as _s
    return _s()


def run(input_path, registry=None, dict_path=None, review=False,
        limit=None, out=None):
    dictionary = load_dict(dict_path)
    name_p = []
    if registry:
        try:
            name_p = name_pairs(nr.load_registry(registry))
        except Exception as e:
            print(f"Реестр не прочитан ({e}) — имена не проверяются.")
    targets = yowords_all(dictionary, name_p)
    if not targets:
        print("Словарь пуст — проверять нечего.")
        return 1

    files = list(iter_text_files(input_path, limit=limit))
    total = len(files)
    print(f"PROGRESS:0/{total}", flush=True)
    hits = []
    stats = {"ё_всего": 0}
    n_pairs = [[w, r, 0] for w, r, _c in targets]
    # 26.10: by_wrong был нужен старой ветке подсчёта (idx выше отключён) —
    # реально считаем перебором targets ниже. Отключено:
    # by_wrong = {w.lower(): idx for idx, (w, r, c) in enumerate(targets)}
    for i, f in enumerate(files, 1):
        if stop_requested():
            print("Остановлено пользователем.")
            break
        for h in scan(f, targets, stats):
            hits.append((h[0], h[1], h[2], h[3], h[4]))
            # 26.10: мёртвое присваивание idx (реальный подсчёт — циклом
            # ниже по targets) — отключено
            # idx = by_wrong.get(h[0].lower())
            # h[0] — написание как в тексте; считаем по словарной форме
            for j, (w, r, c) in enumerate(targets):
                if w.lower() == h[0].lower():
                    n_pairs[j][2] += 1
                    break
        print(f"PROGRESS:{i}/{total}", flush=True)

    print(f"\nСимволов ё в текстах: {stats.get('ё_всего', 0)}"
          " (характер письма проекта).")
    for (w, r, cat), n in zip(targets, n_pairs):
        if n[2]:
            print(f"  [{cat}] {w} / {r}: {n[2]} вхожд.")
    if not hits:
        print("\nПроблемных мест не найдено.")
        return 0
    print(f"\nВсего спорных/несовпадающих вхождений: {len(hits)}.")
    if review:
        for w, r, fs, ln, frag in hits:
            print(f"YO\t{w}\t{r}\t{fs}\t{ln}\t{frag}", flush=True)
    if out:
        _write_report(out, hits, n_pairs, targets)
        print(f"Отчёт: {out}")
    return 0


def _write_report(out, hits, n_pairs, targets):
    lines = ["# Ж/е-аудит", "",
             f"Вхождений к разбору: {len(hits)}.", ""]
    for (w, r, cat), n in zip(targets, n_pairs):
        if n[2]:
            lines.append(f"- [{cat}] {w} / {r}: {n[2]}")
    lines += ["", "| Текст | Правка | Файл | Строка | Фрагмент |",
              "|---|---|---|---|---|"]
    for w, r, fs, ln, frag in hits:
        lines.append(f"| {w} | {r} | {fs} | {ln} | {frag.replace('|', '\\|')} |")
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _replace_cased(text, wrong, right):
    """Замена слова по границам с сохранением первой буквы."""
    rx = _word_pattern(wrong)

    def _sub(m):
        s = m.group(0)
        if s[:1].isupper():
            return right[:1].upper() + right[1:]
        return right

    return rx.sub(_sub, text)


def clean_selection(pairs_by_file):
    """Применяет выбранные правки. pairs_by_file: {файл: [(wrong, right)]}.
    Записи только .md/.txt (docx не трогается — решение пользователя).
    Бэкап в md_replace_backups с датой. Возвращает строки-результаты."""
    results = []
    stamp = _t.strftime("%Y-%m-%d_%H-%M-%S")
    n_files = n_repl = 0
    for fstr, pairs in pairs_by_file.items():
        f = Path(fstr)
        try:
            if not f.is_file() or f.suffix.lower() not in (".md", ".txt"):
                results.append(f"[ПРОПУСК] {f.name}: только .md/.txt")
                continue
            content = f.read_text(encoding="utf-8")
        except (PermissionError, OSError, UnicodeDecodeError) as e:
            results.append(f"[ПРОПУСК] {f.name}: {e}")
            continue
        new = content
        n_pairs = 0
        for w, r in pairs:
            if r and _word_pattern(w).search(new):
                before = new
                new = _replace_cased(new, w, r)
                if new != before:
                    n_pairs += 1
        if n_pairs and new != content:
            bak_dir = f.parent / "md_replace_backups" / stamp
            bak_dir.mkdir(parents=True, exist_ok=True)
            bak = bak_dir / f.name
            if not bak.exists():
                shutil.copy2(f, bak)
            f.write_text(new, encoding="utf-8")
            n_files += 1
            n_repl += len(pairs)
            results.append(f"[Ё] {f}: {len(pairs)} прав(ок)")
    results.append(f"Итого: файлов {n_files}, замено слов {n_repl}.")
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description="ё/е-аудит текста")
    ap.add_argument("--input", required=True, help="папка или файл .md/.txt/.docx")
    ap.add_argument("--registry", help="реестр персонажей (yaml) — имена")
    ap.add_argument("--dict", dest="dict_", help="словарь пар (yaml)")
    ap.add_argument("--review", action="store_true",
                    help="печатать каждое вхождение (YO-строки)")
    ap.add_argument("--limit", type=int, help="брать только первые N файлов")
    ap.add_argument("--out", help="md-отчёт")
    a = ap.parse_args(argv)
    return run(a.input, registry=a.registry, dict_path=a.dict_,
               review=a.review, limit=a.limit, out=a.out)


if __name__ == "__main__":
    sys.exit(main())
