# -*- coding: utf-8 -*-
"""
style_report — стилистический отчёт: повторы слов рядом и длинные предложения.

  python style_report.py --input <папка или файл>
      [--registry characters.yaml] [--window N] [--long N] [--limit N]
      [--out report.md]

Только отчёт — файлы НЕ изменяются.

  1. Повторы: слово встречается второй раз в пределах --window слов
     (по умолчанию 5). Служебные слова, слова короче 4 букв и формы
     персонажей из реестра не учитываются. На одно слово — не больше
     трёх находок, всего — не больше 200.
  2. Длинные предложения: больше --long слов (по умолчанию 25).

Проверка идёт в пределах абзаца — повторы через границу абзаца не считаются.
Блоки кода ``` и frontmatter .md не проверяются.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import text_parser as tp

SKIP_DIRS = {".git", ".obsidian", ".trash", "reports", "__pycache__"}
EXTS = (".md", ".txt", ".docx")
FENCE_RE = ("```", "~~~")

MAX_REPEATS = 200      # всего находок-повторов в отчёте
MAX_LONG = 200         # всего длинных предложений в отчёте
PER_WORD_CAP = 3       # находок на одно слово (иначе затопит отчёт)
FRAG_LEN = 60          # длина фрагмента повтора
SENT_START_LEN = 100   # длина начала длинного предложения

# чисто служебные слова — их повторы не стилистическая проблема
FUNCTION_WORDS = {
    "который", "которая", "которое", "которые", "которого", "которой",
    "которым", "которую", "которых", "которыми",
    "этот", "эта", "это", "эти", "этого", "этой", "этих", "этим", "этими",
    "такой", "такая", "такое", "такие", "такого", "такой",
    "весь", "вся", "все", "всего", "всей", "всех", "всем", "всеми",
    "себя", "себе", "собой",
    "когда", "если", "чтобы", "потому", "поэтому", "затем", "тогда",
    "тоже", "также", "причем", "хотя", "ведь", "либо",
    "быть", "был", "была", "было", "были", "будет", "будут", "буду",
    "есть", "моей", "мой", "моя", "твой", "твоя", "наш", "наша", "ваш",
    "ваша", "ихний", "него", "нее", "ней", "ними", "им", "их", "ему",
    "тут", "там", "здесь", "здеся",
    "при", "под", "над", "про", "без", "тем", "том", "так", "сей",
    "оба", "обе", "три", "два", "сто",
}
STOPWORDS = tp.STOPLIST | FUNCTION_WORDS

WORD_MIN_LEN = 3


def collect(root):
    root = Path(root)
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


def _norm(word):
    return tp.norm_yo(word.lower())


def _paragraphs(text):
    """[(первая_строка, [строки абзаца])] — абзацы разделяются пустой строкой.
    Блоки кода и frontmatter пропускаются."""
    paras = []
    cur, start = None, None
    in_fence = False
    fence_marker = None
    in_fm = False
    for i, line in enumerate(text.split("\n"), 1):
        if in_fm:
            if line.strip() == "---":
                in_fm = False
            continue
        if i == 1 and line.strip() == "---":
            in_fm = True
            continue
        stripped = line.lstrip()
        if stripped.startswith(FENCE_RE):
            if not in_fence:
                in_fence, fence_marker = True, stripped[:3]
            elif stripped.startswith(fence_marker):
                in_fence, fence_marker = False, None
            continue
        if in_fence:
            continue
        if line.strip():
            if cur is None:
                cur, start = [], i
            cur.append(line)
        else:
            if cur:
                paras.append((start, cur))
                cur, start = None, None
    if cur:
        paras.append((start, cur))
    return paras


def scan_repeats(text, window, exclude=None):
    """[(слово, строка, фрагмент)] — повторы в пределах окна слов."""
    exclude = exclude or set()
    hits = []
    per_word = {}
    for start, lines in _paragraphs(text):
        tokens = []
        for ln_off, line in enumerate(lines):
            for m in tp.WORD_RE.finditer(line):
                tokens.append((_norm(m.group(0)), start + ln_off))
        for i, (w, ln) in enumerate(tokens):
            if len(w) < WORD_MIN_LEN or w in STOPWORDS or w in exclude:
                continue
            if per_word.get(w, 0) >= PER_WORD_CAP:
                continue
            for j in range(max(0, i - window), i):
                if tokens[j][0] == w:
                    frag = lines[ln - start].strip()[:FRAG_LEN]
                    hits.append((w, ln, frag))
                    per_word[w] = per_word.get(w, 0) + 1
                    break
    return hits


def scan_long_sentences(text, threshold):
    """[(строка, слов, начало предложения)] — абзацы с предложениями-длинами."""
    hits = []
    for start, lines in _paragraphs(text):
        joined = " ".join(l.strip() for l in lines)
        for sent in tp.sentences(joined):
            n_words = len(tp.WORD_RE.findall(sent))
            if n_words > threshold:
                s = sent.strip()
                hits.append((start, n_words,
                             s[:SENT_START_LEN] + ("…" if len(s) > SENT_START_LEN else "")))
    return hits


def run(input_path, registry=None, window=5, long=25, limit=None, out=None):
    exclude = set()
    if registry:
        try:
            entries = load_registry(registry)
            exclude = {_norm(w) for w in known_forms(entries)}
        except Exception as e:
            print(f"Реестр не прочитан ({e}) — повторы имён не исключаются.")
    files = collect(input_path)
    if limit:
        files = files[:limit]
    if not files:
        print("Файлы .md/.txt/.docx не найдены.")
        return 1

    all_repeats = []   # (слово, файл, строка, фрагмент)
    all_long = []      # (файл, строка, слов, начало)
    total = len(files)
    print(f"PROGRESS:0/{total}", flush=True)
    for idx, f in enumerate(files, 1):
        if tp.stop_requested():
            print("Остановлено пользователем.")
            break
        try:
            if f.suffix.lower() == ".docx":
                from core import docx_io
                text = docx_io.read_text(f)
            else:
                text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError, OSError) as e:
            print(f"ПРОПУСК {f.name}: {e}")
            print(f"PROGRESS:{idx}/{total}", flush=True)
            continue
        print(f"PROGRESS:{idx}/{total}", flush=True)
        reps = scan_repeats(text, window, exclude)
        longs = scan_long_sentences(text, long)
        for w, ln, frag in reps:
            all_repeats.append((w, str(f), ln, frag))
        for ln, nw, s in longs:
            all_long.append((str(f), ln, nw, s))
        if reps or longs:
            print(f"{f}: повторов {len(reps)}, длинных предложений {len(longs)}")

    print(f"\nИтого: повторов рядом {len(all_repeats)} "
          f"(показано до {MAX_REPEATS}), длинных предложений {len(all_long)} "
          f"(показано до {MAX_LONG}); файлов проверено {total}.")

    if out:
        rep = [f"# Стилистика — {input_path}", ""]
        rep += [f"## Повторы рядом (окно {window} слов)", ""]
        if all_repeats:
            for w, fp, ln, frag in all_repeats[:MAX_REPEATS]:
                rep.append(f"- **{w}** — {fp}:{ln} — «{frag}»")
            if len(all_repeats) > MAX_REPEATS:
                rep.append(f"- …и ещё {len(all_repeats) - MAX_REPEATS} (в отчёт не попали)")
        else:
            rep.append("Повторов не найдено.")
        rep += ["", f"## Длинные предложения (больше {long} слов)", ""]
        if all_long:
            for fp, ln, nw, s in all_long[:MAX_LONG]:
                rep.append(f"- {fp}:{ln} ({nw} слов) — «{s}»")
            if len(all_long) > MAX_LONG:
                rep.append(f"- …и ещё {len(all_long) - MAX_LONG} (в отчёт не попали)")
        else:
            rep.append("Длинных предложений не найдено.")
        rep += ["", f"Файлов проверено: {total}."]
        Path(out).write_text("\n".join(rep), encoding="utf-8")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Стилистический отчёт: повторы рядом, длинные предложения")
    ap.add_argument("--input", required=True, help="папка или файл .md/.txt/.docx")
    ap.add_argument("--registry", help="реестр персонажей (исключить формы имён)")
    ap.add_argument("--window", type=int, default=5,
                    help="окно повтора в словах (по умолчанию 5)")
    ap.add_argument("--long", type=int, default=25,
                    help="порог «длинного предложения» в словах (по умолчанию 25)")
    ap.add_argument("--limit", type=int, help="максимум файлов")
    ap.add_argument("--out", help="файл отчёта")
    args = ap.parse_args(argv)
    return run(args.input, registry=args.registry, window=args.window,
               long=args.long, limit=args.limit, out=args.out)


if __name__ == "__main__":
    sys.exit(main())
