# -*- coding: utf-8 -*-
"""core: report — запись отчётов --out (04.11).

Родительские папки создаются на ходу: --out reports/sub/report.md
не падает из-за отсутствующей папки. «--out -» вместо пути печатает
отчёт в stdout — удобно для конвейеров (grep, перенаправление и т.п.).
"""
from pathlib import Path


def write_report(path, text):
    """Пишет текст в path; «-» вместо пути — печатает в stdout."""
    if str(path).strip() == "-":
        print(text)
        return
    p = Path(path)
    parent = p.parent
    if str(parent) not in ("", ".") and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def write_json(path, payload):
    """Пишет JSON-отчёт (indent=2, без экранирования кириллицы).
    «-» вместо пути — печатает в stdout. Родительские папки создаются."""
    import json
    write_report(path, json.dumps(payload, ensure_ascii=False, indent=2))
