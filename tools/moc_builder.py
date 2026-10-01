# -*- coding: utf-8 -*-
"""
moc_builder — авто-генерация MOC-заметок персонажей для Obsidian (01.10).

Для каждого персонажа реестра создаёт заметку «Персонажи/<Имя>.md» со
списком файлов, где он встречается (вики-ссылки [[...]] — Obsidian сам
покажет обратные ссылки). Существующие заметки НЕ перезаписываются
(дополнение по --update добавляет ссылки в конец).

Использование:
  python moc_builder.py --input <vault> --registry <yaml> --out-dir <папка>
  python moc_builder.py --input <vault> --registry <yaml> --out-dir <папка> --apply
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import morph
from core import name_registry as nr
from core import text_parser as tp


def mentions(input_path, registry_path, limit=None):
    """{имя: [относительные пути .md]} — переиспользует логику матрицы."""
    chars = nr.load_registry(registry_path)
    if not chars:
        return chars, {}
    patmap = {c["имя"]: morph.term_patterns([c["имя"]] + list(c["формы"]),
                                            expand=True) for c in chars}
    vault = Path(input_path)
    counts = {c["имя"]: {} for c in chars}
    files = list(tp.iter_text_files(input_path, exts=(".md",), limit=limit))
    total = len(files)
    print(f"PROGRESS:0/{total}", flush=True)
    files_n = 0
    for path in files:
        if tp.stop_requested():
            break
        files_n += 1
        print(f"PROGRESS:{files_n}/{total}", flush=True)
        text = tp.read_text(path)
        if not text:
            continue
        lines = text.splitlines()
        for c in chars:
            n = sum(len(p.findall(ln)) for ln in lines for p in patmap[c["имя"]])
            if n:
                try:
                    rel = path.relative_to(vault)
                except ValueError:
                    rel = Path(path.name)
                counts[c["имя"]][str(rel)] = n
    return chars, counts


def note_text(name, files_map):
    lines = [f"# {name}", "", "Автоматический список заметок с упоминаниями.", ""]
    for rel, n in sorted(files_map.items(), key=lambda kv: -kv[1]):
        stem = str(rel)[:-3] if str(rel).lower().endswith(".md") else str(rel)
        lines.append(f"- {n} — [[{stem}]]")
    lines.append("")
    return "\n".join(lines)


def run(input_path, registry_path, out_dir, limit=None, apply=False, update=False):
    chars, counts = mentions(input_path, registry_path, limit)
    if not chars:
        print(f"Реестр пуст или не найден: {registry_path}")
        return 1
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    print(f"РЕЖИМ: {'СОЗДАНИЕ/ДОПОЛНЕНИЕ' if apply else 'ТОЛЬКО ОБЗОР'}")
    created = updated = skipped = 0
    for c in chars:
        name = c["имя"]
        files_map = counts.get(name, {})
        if not files_map:
            print(f"  [пропуск] {name}: упоминаний нет")
            skipped += 1
            continue
        target = out / f"{name}.md"
        body = note_text(name, files_map)
        if target.exists() and not update:
            print(f"  [есть] {target} (перезапись запрещена; --update допишет)")
            skipped += 1
            continue
        if target.exists() and update:
            old = target.read_text(encoding="utf-8")
            if body.strip() in old:
                skipped += 1
                continue
            if apply:
                with open(target, "a", encoding="utf-8") as f:
                    f.write("\n\n" + body)
            print(f"  [дополнен] {target}")
            updated += 1
        else:
            if apply:
                target.write_text(body, encoding="utf-8")
            print(f"  [создан] {target} ({len(files_map)} файлов)")
            created += 1
    print(f"\nИтого: создано {created}, дополнено {updated}, пропущено {skipped}")
    if not apply:
        print("Обзор — заметки не записаны. Для создания: --apply / галочка.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="MOC-заметки персонажей для Obsidian")
    ap.add_argument("--input", required=True, help="vault/папка с заметками")
    ap.add_argument("--registry", required=True, help="YAML реестр")
    ap.add_argument("--out-dir", required=True,
                    help="папка для заметок (например <vault>/Персонажи)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--apply", action="store_true", help="создать/дополнить")
    ap.add_argument("--update", action="store_true",
                    help="дополнить существующие заметки (перезапись запрещена)")
    args = ap.parse_args(argv)
    return run(args.input, args.registry, args.out_dir, limit=args.limit,
               apply=args.apply, update=args.update)


if __name__ == "__main__":
    sys.exit(main())
