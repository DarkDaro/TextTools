# -*- coding: utf-8 -*-
"""
utf8_convert — проверка и массовое приведение .md/.txt к UTF-8 (01.10).

Старые файлы (koi8-r, cp1251…) раньше молча выпадали из всех проверок.
Здесь: отчёт «какая кодировка у каких файлов» и по --fix перекодировка
в UTF-8 с .bak-бэкапом рядом. .docx — это zip, к нему не применяется.

Использование:
  python utf8_convert.py --input <папка/файл>            — отчёт
  python utf8_convert.py --input <...> --fix             — перекодировать
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import encoding as enc
from core import text_parser as tp


def run(input_path, fix=False, limit=None):
    files = [f for f in tp.iter_text_files(input_path, exts=(".md", ".txt"),
                                           limit=limit)
             if f.suffix.lower() != ".docx"]
    total = len(files)
    print(f"PROGRESS:0/{total}", flush=True)
    print(f"РЕЖИМ: {'ПЕРЕКОДИРОВАТЬ (с .bak)' if fix else 'ТОЛЬКО ОТЧЁТ'}")
    print()

    n_bad = n_fixed = 0
    n = 0
    for f in files:
        n += 1
        if tp.stop_requested():
            print("Остановлено пользователем.")
            break
        if enc.is_utf8(f):
            print(f"PROGRESS:{n}/{total}", flush=True)
            continue
        data = f.read_bytes()
        detected = enc.detect(data)
        n_bad += 1
        if detected is None:
            print(f"  [НЕ ТЕКСТ] {f}")
        else:
            print(f"  [{detected}] {f}")
            if fix and detected not in ("utf-8", "utf-8-sig"):
                try:
                    text = data.decode(detected)
                except (UnicodeDecodeError, LookupError):
                    print(f"      ПРОПУСК: не декодируется как {detected}")
                    n_bad -= 1
                    print(f"PROGRESS:{n}/{total}", flush=True)
                    continue
                shutil.copy2(f, str(f) + ".bak")
                f.write_text(text, encoding="utf-8")
                n_fixed += 1
        print(f"PROGRESS:{n}/{total}", flush=True)

    print()
    if not fix:
        print(f"Не в UTF-8: {n_bad}. Для перекодирования: --fix / галочка «Применить».")
    else:
        print(f"Не в UTF-8: {n_bad}, перекодировано: {n_fixed}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Проверка и приведение текстов к UTF-8")
    ap.add_argument("--input", required=True, help="папка или файл")
    ap.add_argument("--fix", action="store_true",
                    help="перекодировать в UTF-8 (с .bak)")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args(argv)
    return run(args.input, fix=args.fix, limit=args.limit)


if __name__ == "__main__":
    sys.exit(main())
