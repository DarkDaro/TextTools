"""Аудит кнопок интерфейса textools — то, чего не видят клик-тесты.

Пользовательская боль 05.11: «кнопки, которых нет или не видно».
winfo_ismapped() и клик-тесты такие случаи пропускают, поэтому здесь
геометрия проверяется по-честному, на реальных координатах:

1. кнопку создали, но не упаковали — winfo_manager() пуст: command
   есть, клик-тест сочтёт её рабочей, а на экране её нет;
2. кнопка лежит поверх другой кнопки — пересечение прямоугольников
   больше допуска (классическая ловля customtkinter: вторая кнопка
   молча кладётся на первую, тесты проходят, пользователь не видит);
3. кнопку обрезало по ширине карточки или окна — правый край за
   границей видимого контейнера;
4. кнопка нулевого размера или не отрисовалась на выбранной вкладке;
5. кнопка без command; сегмент-селектор без значений.

Скрипт же собирает схему кнопок docs/BUTTONS.md — между маркерами
<!-- BEGIN BUTTON MAP ... --> и <!-- END BUTTON MAP -->. По правилу
«функция ↔ кнопка» схема обновляется вместе с кнопками:

    python test_gui_buttons.py            # аудит + сверка схемы с докой
    python test_gui_buttons.py --md       # напечатать схему в stdout
    python test_gui_buttons.py --fix-docs # перезаписать схему в доке

Расхождение схемы с кодом — провал. Нужен дисплей (в песочнице: Xvfb).
"""
import importlib.util
import sys
import time
import tkinter.font as tkfont
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import customtkinter as ctk

DOCS = HERE / "docs" / "BUTTONS.md"
BEGIN = "<!-- BEGIN BUTTON MAP (генерирует test_gui_buttons.py) -->"
END = "<!-- END BUTTON MAP -->"

KIND_LABEL = {
    # 07.11: зелёного больше нет — было 41 яркую зелёную кнопку, они
    # заливали интерфейс и топили редкие акценты
    "safe": "обычное действие (спокойная)",
    "primary": "ключевое действие (фиолетовая)",
    "danger": "запись (красная)",
    "neutral": "служебная",
    # 07.11: кнопка-открыватель (витрина, журнал, папка) — синяя РАМКА
    # со «▸»: отличается и цветом, и формой
    "open": "открывает окно/список (синяя рамка, ▸)",
}

failures = []


def fail(msg):
    failures.append(msg)
    print(f"  FAIL {msg}")


def load_gui_ctk():
    """gui_ctk лежит .pyw-файлом; если его уже грузил другой тест —
    переиспользуем модуль из sys.modules."""
    if "gui_ctk" in sys.modules:
        return sys.modules["gui_ctk"]
    from importlib.machinery import SourceFileLoader
    path = str(HERE / "gui_ctk.pyw")
    loader = SourceFileLoader("gui_ctk", path)
    spec = importlib.util.spec_from_loader("gui_ctk", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gui_ctk"] = mod
    loader.exec_module(mod)
    return mod


def walk(w):
    yield w
    for child in w.winfo_children():
        yield from walk(child)


def under(w, root):
    """Внутри ли w под root (root — виджет или кортеж виджетов)."""
    roots = tuple(root) if isinstance(root, (tuple, list)) else (root,)
    p = w.master
    while p is not None:
        if any(p is r for r in roots):
            return True
        p = p.master
    return False


def bbox(widget):
    x, y = widget.winfo_rootx(), widget.winfo_rooty()
    return (x, y, x + widget.winfo_width(), y + widget.winfo_height())


def intersects(a, b, tol=4):
    """Перекрытие больше допуска одновременно по X и по Y."""
    dx = min(a[2], b[2]) - max(a[0], b[0])
    dy = min(a[3], b[3]) - max(a[1], b[1])
    return dx > tol and dy > tol


def section_title(section):
    """Заголовок карточки Section — первый лейбл её шапки."""
    head = section.winfo_children()[0] if section.winfo_children() else None
    if head is not None:
        for sub in walk(head):
            if isinstance(sub, ctk.CTkLabel):
                return str(sub.cget("text"))
    return "?"


def kind(b):
    if hasattr(b, "_base_kind"):
        return KIND_LABEL.get(b._base_kind, b._base_kind)
    return "кнопка"


def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


def audit_buttons(where, buttons):
    """Геометрический аудит списка кнопок одной видимой области."""
    # 1) не упакованные и мёртвые
    for b in buttons:
        if not b.winfo_manager():
            fail(f"«{where}»: кнопка «{b.cget('text')}» создана, но не "
                 f"размещена (manager пуст) — её нет на экране")
            continue
        if b.winfo_width() < 6 or b.winfo_height() < 6:
            fail(f"«{where}»: кнопка «{b.cget('text')}» не отрисовалась "
                 f"({b.winfo_width()}x{b.winfo_height()})")
    # 2) перекрытия попарно
    live = [b for b in buttons if b.winfo_manager() and b.winfo_width() >= 6]
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            if intersects(bbox(a), bbox(b)):
                fail(f"«{where}»: кнопка «{b.cget('text')}» лежит поверх "
                     f"«{a.cget('text')}»")
    # 3) без обработчика
    unbound = [b.cget("text") for b in buttons if b.cget("command") is None]
    if unbound:
        fail(f"«{where}»: без command — {unbound[:5]}")
    # 4) обрезанная подпись: CTkLabel молча клипует текст, кнопка
    #    «есть», но пользователь не видит, что она делает
    for b in live:
        text = str(b.cget("text")).strip()
        if not text:
            continue
        try:
            need = tkfont.Font(font=b.cget("font")).measure(text)
        except Exception:
            continue
        if need > b.winfo_width() - 8:
            fail(f"«{where}»: подпись «{text}» обрезана "
                 f"(нужно {need}px, кнопка {b.winfo_width()}px)")


def audit_app(app, print_header=True):
    """Полный аудит по вкладкам + тулбар. Возвращает список проблем."""
    gui = sys.modules["gui_ctk"]
    if print_header:
        print("[кнопки] геометрия: размещение, перекрытия, обрезы")
    saved = app.nb.get()
    total = 0
    for label in list(app._tabs):
        if label == gui.LOG_TAB:
            continue  # журнал — сплошное текстовое поле, карточек нет
        app.nb.set(label)
        for _ in range(8):
            app.update()
            time.sleep(0.04)
        buttons = [w for w in walk(app._tabs[label])
                   if isinstance(w, ctk.CTkButton)
                   and not under(w, _segmented_root(app._tabs[label]))]
        if not buttons:
            fail(f"вкладка «{label}»: не найдено ни одной кнопки — "
                 f"похоже, обход сломался")
        total += len(buttons)
        audit_buttons(f"вкладка «{label}»", buttons)
        # подменю полей пути: правый клик (вставка) и история «▾»
        for w in walk(app._tabs[label]):
            if type(w).__name__ != "PathField":
                continue
            if not str(w.entry.bind("<Button-3>")).strip():
                fail(f"вкладка «{label}»: у поля «{w.key}» нет "
                     f"правого клика (вставка из буфера)")
            btn = getattr(w, "_recent_btn", None)
            if btn is not None and btn.cget("command") is None:
                fail(f"вкладка «{label}»: у поля «{w.key}» история «▾» "
                     f"без обработчика")
        # 4) обрез справа: правый край кнопки за границей скролл-рамки
        scroll = app._tabs[label].master
        for b in buttons:
            if not b.winfo_manager():
                continue
            tol = 2
            br = b.winfo_rootx() + b.winfo_width()
            cr = scroll.winfo_rootx() + scroll.winfo_width()
            if br > cr + tol:
                fail(f"вкладка «{label}»: кнопка «{b.cget('text')}» "
                     f"обрезана справа ({br} > {cr})")
        # 5) селекторы
        for w in walk(app._tabs[label]):
            if isinstance(w, ctk.CTkSegmentedButton) and not w.cget("values"):
                fail(f"вкладка «{label}»: сегмент-селектор без значений")
    # тулбар: кнопки вне Tabview («Стоп» в статусбаре)
    app.nb.set(saved)
    for _ in range(6):
        app.update()
        time.sleep(0.04)
    tb_buttons = [w for w in walk(app)
                  if isinstance(w, ctk.CTkButton) and not under(w, app.nb)
                  and not under(w, app._theme_segment)]
    audit_buttons("тулбар", tb_buttons)
    total += len(tb_buttons)
    # витрина выбора (review_dialog): открывается поверх, свои кнопки,
    # раньше жёсткие 980x640 — на низком экране «Применить» за краем
    dlg = None
    dlg_count = 0
    try:
        import review_dialog
        hits = [("в современном мире", "сегодня", "глава1.md", 5,
                 "В современном мире всё иначе")]
        dlg = review_dialog.show(app, hits, lambda pairs: [])
        for _ in range(8):
            app.update()
            time.sleep(0.04)
        dlg_buttons = [w for w in walk(dlg) if isinstance(w, ctk.CTkButton)]
        dlg_count = len(dlg_buttons)
        audit_buttons("витрина выбора", dlg_buttons)
        # кнопки низа должны целиком попадать в экран по вертикали
        for b in dlg_buttons:
            if b.winfo_manager() and b.winfo_rooty() + b.winfo_height() \
                    > dlg.winfo_screenheight() - 8:
                fail(f"витрина: кнопка «{b.cget('text')}» уходит за "
                     f"нижний край экрана")
    finally:
        if dlg is not None:
            dlg.destroy()
            for _ in range(4):
                app.update()
    total += dlg_count
    print(f"  ok  кнопок на экране: {total}, перекрытий и мёртвых нет"
          if not failures else f"  кнопок на экране: {total}")
    return failures


def _segmented_root(root):
    """Корни сегмент-селекторов: их внутренние кнопки не аудитим."""
    return tuple(w for w in walk(root)
                 if isinstance(w, ctk.CTkSegmentedButton))


def collect_map(app):
    """Схема: вкладка → карточка → кнопки/галочки/селекторы в порядке
    создания. Возвращает строки markdown."""
    gui = sys.modules["gui_ctk"]
    saved = app.nb.get()
    lines = []

    tb_rows = []
    for w in walk(app):
        if under(w, app.nb) or under(w, app._theme_segment):
            continue
        if isinstance(w, ctk.CTkSegmentedButton):
            vals = ", ".join(w.cget("values"))
            tb_rows.append(f"| селектор темы | сегменты | {vals} |")
        elif isinstance(w, ctk.CTkButton):
            tb_rows.append(f"| {esc(w.cget('text'))} | {kind(w)} | "
                           f"{esc(getattr(w, 'tooltip_text', '')) or '—'} |")
    if tb_rows:
        lines.append("## Шапка и статусбар (вне вкладок)")
        lines.append("")
        lines.append("| Элемент | Тип | Действие / значения |")
        lines.append("|---|---|---|")
        lines.extend(tb_rows)
        lines.append("")

    for label in list(app._tabs):
        if label == gui.LOG_TAB:
            continue
        app.nb.set(label)
        for _ in range(6):
            app.update()
            time.sleep(0.04)
        lines.append(f"## Вкладка «{label}»")
        lines.append("")
        current = None
        for w in walk(app._tabs[label]):
            if type(w).__name__ == "Section":
                current = section_title(w)
                if lines and lines[-1] != "":
                    lines.append("")
                lines.append(f"### {current}")
                lines.append("")
                lines.append("| Элемент | Тип | Действие / значения |")
                lines.append("|---|---|---|")
                continue
            if current is None:
                continue  # вне карточек порядок не описываем
            if isinstance(w, ctk.CTkButton) and not under(
                    w, _segmented_root(app._tabs[label])):
                tip = esc(getattr(w, "tooltip_text", ""))
                lines.append(f"| {esc(w.cget('text'))} | {kind(w)} | "
                             f"{tip or '—'} |")
            elif isinstance(w, ctk.CTkCheckBox):
                txt = esc(w.cget("text")) or "(без подписи)"
                lines.append(f"| {txt} | галочка | — |")
            elif isinstance(w, ctk.CTkSegmentedButton):
                vals = ", ".join(w.cget("values"))
                lines.append(f"| селектор | сегменты | {vals} |")
        lines.append("")
    app.nb.set(saved)
    for _ in range(4):
        app.update()
    return lines


def build_doc(lines):
    return (BEGIN + "\n" + "\n".join(lines) + "\n" + END + "\n")


def docs_section():
    if not DOCS.exists():
        return None
    text = DOCS.read_text(encoding="utf-8")
    i, j = text.find(BEGIN), text.find(END)
    if i < 0 or j < 0:
        return None
    return text[i:j + len(END)]


def check_sync(lines, out=print):
    """Схема в доке == схема из кода?"""
    want = build_doc(lines).strip()
    have = (docs_section() or "").strip()
    if want == have:
        out("  ok  схема docs/BUTTONS.md синхронна с кодом")
        return True
    out("  FAIL docs/BUTTONS.md расходится с кнопками в коде")
    out("       обновите схему: python test_gui_buttons.py --fix-docs")
    wl, hl = want.splitlines(), have.splitlines()
    for n, (a, b) in enumerate(zip(wl, hl), 1):
        if a != b:
            out(f"       первая разница, строка {n}:")
            out(f"       код:  {a[:96]}")
            out(f"       дока: {b[:96]}")
            break
    else:
        out(f"       разница длины: код {len(wl)} строк, дока {len(hl)}")
    return False


def fix_docs(lines):
    old = DOCS.read_text(encoding="utf-8") if DOCS.exists() else None
    if old is None or BEGIN not in old or END not in old:
        DOCS.parent.mkdir(exist_ok=True)
        DOCS.write_text(old or "", encoding="utf-8")
        raise SystemExit("в docs/BUTTONS.md нет маркеров схемы — "
                         "вставьте «" + BEGIN + "» и «" + END + "»")
    i = old.find(BEGIN)
    j = old.find(END) + len(END)
    DOCS.write_text(old[:i] + build_doc(lines).rstrip("\n") + old[j:],
                    encoding="utf-8")
    print(f"  ok  docs/BUTTONS.md обновлён ({len(lines)} строк схемы)")


def main():
    argv = sys.argv[1:]
    gui_config = __import__("gui_config")
    gui_ctk = load_gui_ctk()
    app = None
    try:
        app = gui_ctk.App()
        for _ in range(6):
            app.update()
            time.sleep(0.1)
        lines = collect_map(app)
        if "--md" in argv:
            print(build_doc(lines))
            return 0
        if "--fix-docs" in argv:
            fix_docs(lines)
            return 0
        print("[кнопки] схема")
        ok = check_sync(lines)
        audit_app(app)
        if not failures and ok:
            print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
            return 0
        print(f"ПРОВАЛ: {len(failures) + (0 if ok else 1)}")
        return 1
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
        gui_config.reset()


if __name__ == "__main__":
    sys.exit(main())
