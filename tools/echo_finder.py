# -*- coding: utf-8 -*-
"""
echo_finder — «эхо-фразы»: повторы конструкций МЕЖДУ разными файлами
(05.11, BACKLOG №6).

Главный стилистический грех длинной рукописи — повтор приёма через
главу: «мир сжался», «задышал ровнее». Внутри одного файла повторы
ловит style-report, между файлами не ловил никто.

Механика: текст режется на предложения, каждое нормализуется
(нижний регистр, ё=е) и разбирается на n-граммы (по умолчанию 3
слова). Эхо — n-грамм, встретившийся в >= --min-files РАЗНЫХ файлах.
Подавление шума:
  - служебные слова (ECHO_STOPS): n-грамм только из них не считается;
  - имена реестра (--registry): их формы исключаются из n-граммов —
    «Кай посмотрел» не эхо, а сюжет;
  - топ-N (--top, по умолчанию 25) и честная подача: это не ошибки,
    а повод перечитать места.

Код возврата: 0 — эхо не найдено, 1 — найдено (как у cjk), 2 —
ошибка путей.

Использование:
  python textools.py echo --input папка [--n 3] [--min-files 2]
      [--top 25] [--registry реестр.yaml] [--out отчёт.md] [--json -]
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import text_parser as tp
from core.report import write_report, write_json

# служебные слова: сами по себе конструкции не образуют
# (нормализованы ё=е, нижний регистр)
ECHO_STOPS = frozenset("""
в во не ни на по с со из изо у за до от об о обо про через сквозь над
под перед между и а но да или либо же бы б ли то это этот эта эти тот
та те там тут здесь когда если чтобы потому поэтому зато впрочем
однако ведь вот вон даже уже еще только потом тогда как что кто все
весь вся всё весь свой своя мое моя мой твой твоя наш ваш себя кто
что куда откуда зачем можно нельзя нужно надо пусть пусть даже почти
был была было были будет будут быть есть нет ни-будь -то -либо
""".split())

# свой токенизатор: В ОТЛИЧИЕ от tp.WORD_RE держит слова из одной
# буквы — «мир сжался до точки» без «до» уже не та конструкция
ECHO_WORD_RE = re.compile(r"[а-яёa-z]+(?:-[а-яёa-z]+)*")


def _words(sentence):
    """Слова предложения: нижний регистр, ё=е, предлоги сохраняются."""
    return ECHO_WORD_RE.findall(tp.norm_yo(sentence.lower()))


def _is_noise(ngram_words):
    """n-грамм из одних служебных слов конструкции не образует."""
    return all(w in ECHO_STOPS for w in ngram_words)


def load_name_words(registry_path):
    """Имена и ВСЕ варианты реестра (формы, старые, опечатки) —
    исключаются из эха. Составные имена («Мастер Линь») добавляются
    и по отдельным словам: n-граммы сравниваются по одному слову."""
    from core import name_registry as nr
    words = set()
    for c in nr.load_registry(registry_path):
        vals = [c.get("имя") or ""]
        for key in ("формы", "старое", "старое_опасное", "опечатки"):
            vals.extend(c.get(key) or [])
        for f in vals:
            f = str(f).strip()
            if not f:
                continue
            norm = tp.norm_yo(f.lower())
            words.add(norm)
            # составные имена исключаем и по словам
            words.update(w for w in norm.split() if len(w) >= 3)
    return words


def find_echo(input_path, n=3, min_files=2, top=25, name_words=None,
              limit=None):
    """Сканирование хранилища. Возвращает список находок:
    [{"ngram", "files", "count", "example": {"file", "sentence"}}],
    отсортированный по (файлов, раз, сама фраза)."""
    name_words = name_words or set()
    counts = defaultdict(int)          # n-грамм -> всего вхождений
    file_sets = defaultdict(set)       # n-грамм -> {файл}
    examples = {}                      # n-грамм -> (файл, предложение)

    files = list(tp.iter_text_files(input_path, limit=limit,
                                   exts=tp.ANALYSIS_EXTS))  # 07.11: + html
    for f in files:
        text = tp.read_text(f)
        if not text:
            continue
        for sent in tp.sentences(text):
            if not sent.strip():
                continue
            words = _words(sent)
            if len(words) < n:
                continue
            for i in range(len(words) - n + 1):
                chunk = words[i:i + n]
                if _is_noise(chunk):
                    continue
                if name_words and any(w in name_words for w in chunk):
                    continue
                gram = " ".join(chunk)
                counts[gram] += 1
                file_sets[gram].add(str(f))
                if gram not in examples:
                    frag = " ".join(sent.split())
                    examples[gram] = (str(f),
                                      frag[:80] + ("…" if len(frag) > 80 else ""))

    items = []
    for gram, total in counts.items():
        fs = file_sets[gram]
        if len(fs) < min_files:
            continue
        ef, es = examples[gram]
        items.append({"ngram": gram, "files": len(fs), "count": total,
                      "example": {"file": ef, "sentence": es}})
    items.sort(key=lambda it: (-it["files"], -it["count"], it["ngram"]))
    if top is not None and top > 0:
        items = items[:top]
    return items


def _echo_text(items, input_path, n, min_files):
    head = (f"Эхо-фразы (n={n}, минимум файлов: {min_files}): "
            f"{len(items)} находок")
    L = [head, ""]
    if not items:
        L.append("Межфайловых повторов конструкций не найдено — "
                 "каждая глава звучит по-своему.")
        return "\n".join(L) + "\n"
    for it in items:
        L.append(f"«{it['ngram']}» — файлов: {it['files']}, "
                 f"раз: {it['count']}")
        L.append(f"    {it['example']['file']}: "
                 f"«{it['example']['sentence']}»")
    L.append("")
    L.append("Это не ошибки: повтор приёма через главу — повод "
             "перечитать места и решить по контексту.")
    return "\n".join(L) + "\n"


def run(input_path, n=3, min_files=2, top=25, registry=None, out=None,
        json_out=None, limit=None):
    name_words = load_name_words(registry) if registry else set()
    items = find_echo(input_path, n=n, min_files=min_files, top=top,
                      name_words=name_words, limit=limit)
    print(_echo_text(items, input_path, n, min_files), end="")
    if out:
        # md-версия: таблица + примеры
        L = [f"# Эхо-фразы (n={n}, минимум файлов: {min_files})", ""]
        if items:
            L += ["| Конструкция | Файлов | Раз | Пример |",
                  "|---|---|---|---|"]
            for it in items:
                ex = it["example"]["sentence"].replace("|", "\\|")
                L.append(f"| {it['ngram']} | {it['files']} | "
                         f"{it['count']} | {ex} |")
            L += ["", "Повтор приёма через главу — повод перечитать "
                      "места и решить по контексту."]
        else:
            L.append("Межфайловых повторов конструкций не найдено.")
        write_report(out, "\n".join(L) + "\n")
        if str(out).strip() != "-":
            print(f"Отчёт: {out}")
    if json_out:
        payload = {"tool": "echo", "input": str(input_path), "n": n,
                   "min_files": min_files, "total": len(items),
                   "items": items}
        write_json(json_out, payload)
        if str(json_out).strip() != "-":
            print(f"JSON-отчёт: {json_out}")
    return 1 if items else 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="echo",
        description="«Эхо-фразы»: повторы конструкций между файлами")
    ap.add_argument("--input", required=True, help="папка или файл")
    ap.add_argument("--n", type=int, default=3,
                    help="слов в конструкции (по умолчанию 3)")
    ap.add_argument("--min-files", type=int, default=2,
                    help="минимум разных файлов (по умолчанию 2)")
    ap.add_argument("--top", type=int, default=25,
                    help="показать первые N находок (по умолчанию 25)")
    ap.add_argument("--registry",
                    help="реестр персонажей (yaml) — имена исключаются")
    ap.add_argument("--limit", type=int, help="максимум файлов")
    ap.add_argument("--out", help="отчёт в .md («-» — в stdout)")
    ap.add_argument("--json", dest="json_out",
                    help="полный список в JSON («-» — в stdout)")
    args = ap.parse_args(argv)
    if not 2 <= args.n <= 6:
        print("Ошибка: --n должен быть от 2 до 6 слов.", file=sys.stderr)
        return 2
    if args.min_files < 2:
        print("Ошибка: --min-files минимум 2 — повторы внутри одного "
              "файла ловит style-report.", file=sys.stderr)
        return 2
    try:
        return run(args.input, n=args.n, min_files=args.min_files,
                   top=args.top, registry=args.registry, out=args.out,
                   json_out=args.json_out, limit=args.limit)
    except ValueError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
