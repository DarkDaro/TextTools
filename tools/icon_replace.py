# -*- coding: utf-8 -*-
"""
icon_replace — замена эмодзи-иконок на inline-SVG в HTML (04.11).

Интерфейсные эмодзи (💰 ❤️ ⏩ …) в HTML-файлах заменяются на векторные
SVG-иконки: они выглядят одинаково на любой системе и не зависят от
шрифтов эмодзи. Рядом с заменами добавляется блок CSS-стилей .ic/.sicon.

По умолчанию — только отчёт. Реальная замена: --fix (копия .bak рядом
с файлом создаётся автоматически). Повторный запуск безопасен: уже
обработанные файлы пропускаются.

Использование:
  python tools/icon_replace.py --input <файл/папка>            — отчёт
  python tools/icon_replace.py --input <...> --fix             — заменить
  python tools/icon_replace.py --input <...> --map icons.json  — свои иконки
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import text_parser as tp

# Расширения файлов, которые обрабатываются при обходе папки
DEFAULT_EXTS = (".html", ".htm")

# Признак обработанного файла: блок стилей уже добавлен
DONE_MARK = ".ic .sicon"


def svg(body, vb="0 0 24 24"):
    return ('<svg class="sicon" viewBox="' + vb
            + '" xmlns="http://www.w3.org/2000/svg">' + body + "</svg>")


GOLD = "#ffcf7a"; GOLD_D = "#9a6a10"; RED = "#ff5a4a"; BLUE = "#8ecbff"
MANA = "#a58cff"; GREEN = "#7dd87a"; FIRE = "#ff8a3c"; STONE = "#c9c2b4"

# Встроенный набор: эмодзи -> HTML-замена (inline-SVG).
ICONS = {
    "💰": '<span class="ic ic-gold">' + svg(
        '<circle cx="12" cy="12" r="8" fill="' + GOLD + '" stroke="'
        + GOLD_D + '" stroke-width="2"/><circle cx="12" cy="12" r="4.5" '
        'fill="none" stroke="' + GOLD_D + '" stroke-width="1.5"/>'
        '<path d="M12 9v6" stroke="' + GOLD_D + '" stroke-width="1.5"/>') + "</span>",
    "❤️": '<span class="ic ic-red">' + svg(
        '<path d="M12 20C6 15 3.5 11.5 3.5 8.5 3.5 6 5.5 4 8 4c1.7 0 3.2 1 '
        '4 2.4C12.8 5 14.3 4 16 4c2.5 0 4.5 2 4.5 4.5 0 3-2.5 6.5-8.5 '
        '11.5z" fill="' + RED + '" stroke="#5a0e0e" stroke-width="1.4"/>') + "</span>",
    "🌊": '<span class="ic ic-blue">' + svg(
        '<path d="M2 15c2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2 2.5 2 5 2" '
        'fill="none" stroke="' + BLUE + '" stroke-width="2.2" '
        'stroke-linecap="round"/><path d="M2 19c2.5 0 2.5-2 5-2s2.5 2 5 2 '
        '2.5-2 5-2 2.5 2 5 2" fill="none" stroke="' + BLUE + '" '
        'stroke-width="2.2" stroke-linecap="round" opacity="0.6"/>') + "</span>",
    "🔮": '<span class="ic ic-mana">' + svg(
        '<circle cx="12" cy="12" r="8" fill="' + MANA + '" stroke="#3a2470" '
        'stroke-width="2"/><ellipse cx="9.5" cy="9" rx="2.6" ry="1.6" '
        'fill="#ffffff" opacity="0.75"/><path d="M6 19l6 3 6-3" fill="none" '
        'stroke="#3a2470" stroke-width="2" stroke-linecap="round"/>') + "</span>",
    "⏯️": '<span class="ic">' + svg(
        '<rect x="5" y="5" width="4.5" height="14" rx="1" fill="' + STONE
        + '"/><rect x="14.5" y="5" width="4.5" height="14" rx="1" fill="'
        + STONE + '"/>') + "</span>",
    "▶": '<span class="ic">' + svg(
        '<path d="M7 4l13 8-13 8z" fill="' + STONE + '"/>') + "</span>",
    "⏩": '<span class="ic">' + svg(
        '<path d="M4 4l9 8-9 8z" fill="' + STONE + '"/>'
        '<path d="M12 4l9 8-9 8z" fill="' + STONE + '"/>') + "</span>",
    "🔁": '<span class="ic">' + svg(
        '<path d="M6 12a6 6 0 0110.5-4" fill="none" stroke="' + STONE
        + '" stroke-width="2.4" stroke-linecap="round"/>'
        '<path d="M17 4v4h-4" fill="none" stroke="' + STONE
        + '" stroke-width="2.4" stroke-linecap="round"/>'
        '<path d="M18 12a6 6 0 01-10.5 4" fill="none" stroke="' + STONE
        + '" stroke-width="2.4" stroke-linecap="round"/>'
        '<path d="M7 20v-4h4" fill="none" stroke="' + STONE
        + '" stroke-width="2.4" stroke-linecap="round"/>') + "</span>",
    "🔄": '<span class="ic">' + svg(
        '<path d="M20 12a8 8 0 11-2.3-5.6" fill="none" stroke="' + GOLD
        + '" stroke-width="2.6" stroke-linecap="round"/>'
        '<path d="M20 3v5h-5" fill="none" stroke="' + GOLD
        + '" stroke-width="2.6" stroke-linecap="round"/>') + "</span>",
    "🔊": '<span class="ic ic-gold">' + svg(
        '<path d="M4 9v6h4l5 4V5L8 9z" fill="' + STONE + '"/>'
        '<path d="M16 9a4 4 0 010 6" fill="none" stroke="' + GOLD
        + '" stroke-width="2" stroke-linecap="round"/>'
        '<path d="M18.5 6.5a8 8 0 010 11" fill="none" stroke="' + GOLD
        + '" stroke-width="2" stroke-linecap="round"/>') + "</span>",
    "🔇": '<span class="ic ic-dim">' + svg(
        '<path d="M4 9v6h4l5 4V5L8 9z" fill="' + STONE + '"/>'
        '<path d="M16 9l6 6M22 9l-6 6" stroke="' + RED
        + '" stroke-width="2.2" stroke-linecap="round"/>') + "</span>",
    "⚡": '<span class="ic ic-gold">' + svg(
        '<path d="M13 2L5 14h5l-1.5 8L19 9h-5.5z" fill="' + GOLD
        + '" stroke="' + GOLD_D + '" stroke-width="1.2"/>') + "</span>",
    "❄️": '<span class="ic ic-blue">' + svg(
        '<g stroke="' + BLUE + '" stroke-width="2" stroke-linecap="round">'
        '<path d="M12 2v20M4 6l16 12M20 6L4 18"/></g>') + "</span>",
    "🔥": '<span class="ic ic-fire">' + svg(
        '<path d="M12 2c1 4-3 5.5-3 9a3 3 0 006 0c0-1.5-.8-2.5-.8-2.5 '
        '2.3 1 4.3 3.4 4.3 6A6.5 6.5 0 015.5 15C5.5 9 11 7.5 12 2z" '
        'fill="' + FIRE + '" stroke="#7a2400" stroke-width="1.3"/>'
        '<path d="M12 21a3 3 0 01-3-3c0-1.6 1.6-2.6 3-4 1.4 1.4 3 2.4 '
        '3 4a3 3 0 01-3 3z" fill="#ffd75e"/>') + "</span>",
    "💨": '<span class="ic ic-dim">' + svg(
        '<path d="M3 9h11a2.5 2.5 0 10-2.5-2.5M3 13h15a2.5 2.5 0 11-2.5 '
        '2.5M3 17h8" fill="none" stroke="' + STONE
        + '" stroke-width="2" stroke-linecap="round"/>') + "</span>",
    "🛡️": '<span class="ic ic-blue">' + svg(
        '<path d="M12 3l7 3v5c0 5-3.2 8.4-7 10-3.8-1.6-7-5-7-10V6z" '
        'fill="#4a6a9a" stroke="' + BLUE + '" stroke-width="1.6"/>'
        '<path d="M12 3v18" stroke="' + BLUE
        + '" stroke-width="1.2"/>') + "</span>",
    "💚": '<span class="ic">' + svg(
        '<path d="M12 20C6 15 3.5 11.5 3.5 8.5 3.5 6 5.5 4 8 4c1.7 0 3.2 1 '
        '4 2.4C12.8 5 14.3 4 16 4c2.5 0 4.5 2 4.5 4.5 0 3-2.5 6.5-8.5 '
        '11.5z" fill="' + GREEN + '" stroke="#1d4a1d" '
        'stroke-width="1.4"/>') + "</span>",
    "✨": '<span class="ic ic-gold">' + svg(
        '<path d="M12 3l1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6z" '
        'fill="' + GOLD + '"/><circle cx="19" cy="18" r="1.6" fill="' + GOLD
        + '"/><circle cx="5" cy="17" r="1.2" fill="' + GOLD + '"/>') + "</span>",
    "🌙": '<span class="ic ic-blue">' + svg(
        '<path d="M20 14.5A8.5 8.5 0 019.5 4 8.5 8.5 0 1020 '
        '14.5z" fill="' + BLUE + '" stroke="#2a4a70" '
        'stroke-width="1.4"/>') + "</span>",
    "🌫️": '<span class="ic ic-dim">' + svg(
        '<path d="M3 9c3 0 3-2 6-2s3 2 6 2 3-2 6-2M3 14c3 0 3-2 6-2s3 2 6 2 '
        '3-2 6-2M3 19c3 0 3-2 6-2s3 2 6 2 3-2 6-2" fill="none" stroke="'
        + STONE + '" stroke-width="1.8" stroke-linecap="round" '
        'opacity="0.85"/>') + "</span>",
}

CSS = """
        /* --- SVG-иконки интерфейса (tools/icon_replace.py) --- */
        .ic { display: inline-flex; vertical-align: -0.18em; }
        .ic .sicon { width: 1.12em; height: 1.12em; display: block; filter: drop-shadow(0 1px 1px rgba(0,0,0,0.8)); }
        .ic-gold { color: #ffcf7a; }
        .ic-red { color: #ff5a4a; }
        .ic-blue { color: #8ecbff; }
        .ic-mana { color: #a58cff; }
        .ic-fire { color: #ff8a3c; }
        .ic-dim { color: #c9c2b4; opacity: 0.85; }
"""

# Служебные присвоения textContent, которые переводятся на innerHTML
# даже без эмодзи в строке: в них попадают сообщения, собранные из
# частей, уже содержащих SVG-иконки.
MARKERS = ("wave-display", "t.textContent = msg")


def load_map(map_file):
    """Свой набор замен из JSON: {"эмодзи": "<span ...>...</span>"}.
    Пары дополняют встроенный набор и переопределяют одноимённые."""
    data = json.loads(Path(map_file).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON замен должен быть объектом {эмодзи: HTML}")
    icons = dict(ICONS)
    for k, v in data.items():
        if not isinstance(v, str) or not v:
            raise ValueError(f"Пустая замена для {k!r} в {map_file}")
        icons[str(k)] = v
    return icons


def _convert_assignments(lines, emoji_re, use_markers):
    """Строки присвоения .textContent с эмодзи переводятся на .innerHTML:
    в значении теперь HTML-разметка SVG, текстовым присвоением её не
    показать. Возвращает число изменённых строк."""
    converted = 0
    for i, ln in enumerate(lines):
        if ".textContent = " not in ln:
            continue
        if emoji_re.search(ln) or (use_markers
                                   and any(m in ln for m in MARKERS)):
            lines[i] = ln.replace(".textContent = ", ".innerHTML = ", 1)
            converted += 1
    return converted


def transform(text, icons, use_markers=True):
    """Заменить эмодзи на SVG в тексте файла.

    Возвращает (новый текст, {эмодзи: сколько}, изменённых присвоений).
    Если эмодзи из набора нет, текст возвращается как есть."""
    order = sorted(icons.keys(), key=len, reverse=True)
    emoji_re = re.compile("|".join(re.escape(e) for e in order))

    counts = {}

    def _rep(m):
        e = m.group(0)
        counts[e] = counts.get(e, 0) + 1
        return icons[e]

    lines = text.split("\n")
    converted = _convert_assignments(lines, emoji_re, use_markers)
    new_text = emoji_re.sub(_rep, "\n".join(lines))
    return new_text, counts, converted


def run(input_path, fix=False, exts=None, no_bak=False, limit=None,
        out=None, map_file=None, no_markers=False):
    exts = exts or DEFAULT_EXTS
    icons = load_map(map_file) if map_file else dict(ICONS)
    use_markers = not no_markers
    lines_out = []

    def _say(msg=""):
        print(msg)
        lines_out.append(msg)

    try:
        files = [f for f in tp.iter_text_files(
                     input_path, exts=tuple(exts), limit=limit)
                 if f.suffix.lower() != ".bak"]
    except ValueError as e:
        print(f"ОШИБКА: {e}")
        return 1

    total = len(files)
    print(f"PROGRESS:0/{total}", flush=True)
    # 04.11: выбор режима до f-строки — перенос выражения внутри
    # f-string ломает Python 3.10/3.11 (разрешён только с 3.12)
    if fix and no_bak:
        mode = "ЗАМЕНА (без бэкапа)"
    elif fix:
        mode = "ЗАМЕНА (с .bak)"
    else:
        mode = "ТОЛЬКО ОТЧЁТ"
    _say(f"РЕЖИМ: {mode}")
    _say()

    n_done = n_emoji = n_skip = 0
    for i, f in enumerate(files, 1):
        if tp.stop_requested():
            _say("Остановлено пользователем.")
            break
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            _say(f"  [ПРОПУСК] {f}: {e}")
            print(f"PROGRESS:{i}/{total}", flush=True)
            continue
        if DONE_MARK in text:
            n_skip += 1
            _say(f"  [уже SVG] {f}")
            print(f"PROGRESS:{i}/{total}", flush=True)
            continue
        new_text, counts, converted = transform(text, icons, use_markers)
        if not counts and not converted:
            print(f"PROGRESS:{i}/{total}", flush=True)
            continue
        n_done += 1
        n_emoji += sum(counts.values())
        top = ", ".join(f"{e}×{c}" for e, c in
                        sorted(counts.items(), key=lambda kv: -kv[1])[:6])
        _say(f"  [{sum(counts.values())} иконок]"
             f" {f}: {top}"
             + (f", присвоений innerHTML: {converted}" if converted else ""))
        if fix:
            if not no_bak:
                tp.backup_once(f)
            if "</style>" in new_text:
                new_text = new_text.replace("</style>", CSS + "    </style>",
                                            1)
            else:
                _say(f"      ВНИМАНИЕ: {f.name}: не найден </style>, "
                     "стили иконок не добавлены")
            f.write_text(new_text, encoding="utf-8")
        print(f"PROGRESS:{i}/{total}", flush=True)

    _say()
    if fix:
        _say(f"Итог: файлов изменено {n_done}, иконок {n_emoji}, "
             f"уже обработано {n_skip}.")
    else:
        _say(f"Итог: файлов к изменению {n_done}, иконок {n_emoji}. "
             "Для замены: --fix / галочка «Применить».")
    if out:
        try:
            Path(out).write_text("\n".join(lines_out) + "\n",
                                 encoding="utf-8")
        except OSError as e:
            print(f"ОШИБКА: не записан отчёт {out}: {e}")
            return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Замена эмодзи-иконок на inline-SVG в HTML")
    ap.add_argument("--input", required=True, help="папка или файл")
    ap.add_argument("--fix", action="store_true",
                    help="заменить иконки (по умолчанию только отчёт)")
    ap.add_argument("--ext", default="html,htm",
                    help="расширения через запятую (по умолчанию html,htm)")
    ap.add_argument("--no-bak", action="store_true",
                    help="не делать .bak-копию (для папок под git)")
    ap.add_argument("--no-markers", action="store_true",
                    help="не переводить служебные textContent-присвоения "
                         "без эмодзи на innerHTML")
    ap.add_argument("--map", dest="map_file",
                    help="JSON со своими заменами: {\"эмодзи\": HTML}")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", help="сохранить отчёт в файл")
    args = ap.parse_args(argv)
    return run(args.input, fix=args.fix,
               exts=[(e if e.startswith(".") else "." + e) for e in
                     (x.strip().lower() for x in
                      args.ext.replace(";", ",").split(",")) if e],
               no_bak=args.no_bak, limit=args.limit, out=args.out,
               map_file=args.map_file, no_markers=args.no_markers)


if __name__ == "__main__":
    sys.exit(main())
