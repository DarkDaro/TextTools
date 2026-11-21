# -*- coding: utf-8 -*-
"""
cli_smoke — смоук-прогон всех CLI-подкоманд разом (команда smoke,
21.11). Повышение из рабочего скрипта песочницы polygon_run.py —
закрывает TD-04 «нет смоук-прогона всех CLI-подкоманд».

Как работает: read-only команды идут по полигону test/demo_garbage/vault
(он в репозитории именно для этого), пишущие — по временной копии
полигона, личные данные и исходники не трогаются. Сводка: команда →
код выхода → время → ключевые строки вывода.

Вердикты: код 0 — ок; код 1 — штатные находки (у поисковых инструментов
«нашёл проблемы» = 1, так задумано); код 2 и выше или Traceback —
ПРОВАЛ. update не гоняется вовсе — единственная сетевая команда.
Код выхода smoke: 0 — провалов нет, 1 — есть.
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "test" / "demo_garbage" / "vault"
REGISTRY = VAULT / "registry.yaml"
CANDIDATES = ROOT / "test" / "demo_garbage" / "candidates.yaml"

# read-only: по оригиналу полигона
READ_ONLY = [
    ["registry-builder", "--input", "{vault}", "--out", "-"],
    ["consistency", "--input", "{vault}", "--registry", "{reg}"],
    ["forms", "--registry", "{reg}"],
    ["matrix", "--input", "{vault}", "--registry", "{reg}", "--out", "-"],
    ["stats", "--input", "{vault}"],
    ["moc", "--input", "{vault}", "--registry", "{reg}", "--out-dir", "-"],
    ["orphan-finder", "--input", "{vault}"],
    ["broken-links", "--input", "{vault}"],
    ["merge-finder", "--input", "{vault}"],
    ["integrity", "--input", "{vault}"],
    ["obsidian-check", "--input", "{vault}", "--exit-zero"],
    ["cjk", "--input", "{vault}", "--exit-zero"],
    ["typography", "--input", "{vault}"],
    ["style-report", "--input", "{vault}", "--registry", "{reg}"],
    ["whitespace", "--input", "{vault}"],
    ["separators", "--input", "{vault}"],
    ["phrase-check", "--input", "{vault}"],
    ["echo", "--input", "{vault}"],
    ["antiresolve", "--input", "{vault}"],
    ["pathos", "--input", "{vault}"],
    ["name-check", "--name", "Мира"],
    ["check-all", "--input", "{vault}"],
    ["meta-check"],
    ["doctor"],
    ["export-docx", "--input", "{vault_md}", "--out", "{tmp_docx}"],
]

# пишущие: по временной копии полигона
WRITE = [
    ["utf8", "--input", "{copy}", "--fix"],
    ["obsidian-check", "--input", "{copy}", "--fix", "--no-bak"],
    ["typography", "--input", "{copy}", "--fix"],
    ["whitespace", "--input", "{copy}", "--fix"],
    ["separators", "--input", "{copy}", "--fix"],
    ["emoji-icons", "--input", "{copy}"],
    ["restore", "--input", "{copy}"],
    ["archive-backups", "--input", "{copy}", "--move"],
    ["merge-registry", "--candidates", "{cand}", "--registry",
     "{copy_reg}", "--add"],
]

# намеренно пропускаются: суть + причина
SKIP = [("update", "сетевая команда — смоук ходит только по локальным"),
        ("smoke", "сам себя не гоняет"),
        ("yo", "требует ё-словарь/интерактивный ввод — покрывается pytest"),
        ("utf8", "(без --fix)"), ]

# строки, которые считаем ключевыми в выводе команды
KEEP = ("ОШИБКА", "ERROR", "Error", "Traceback", "готово", "найдено",
        "итог", "Итого", "не найдено", "PROGRESS", "Код", "замен",
        "правка", "Предохранитель")


def _one(cmd, timeout=300):
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, cwd=ROOT)
        return p.returncode, p.stdout, p.stderr, time.time() - t0
    except Exception as e:
        return -1, "", f"запуск не удался: {e}", time.time() - t0


def _report(title, specs, log, fill):
    log("=" * 72)
    log(title)
    fails = 0
    for spec in specs:
        name = spec[0]
        cmd = [sys.executable, str(ROOT / "textools.py")] + fill(spec)
        code, out, err, dt = _one(cmd)
        bad = code not in (0, 1) or "Traceback" in out or "Traceback" in err
        if bad:
            fails += 1
        log(f"[{code:>2}] {name:<16} {dt:5.1f}s"
            + ("  ПРОВАЛ" if bad else ""))
        lines = [l for l in (out.splitlines() + err.splitlines()) if l.strip()]
        key = [l for l in lines if any(k in l for k in KEEP)]
        for l in key[:4]:
            log("      " + l[:150])
        if bad:
            for l in lines[-6:]:
                log("      ! " + l[:150])
    return fails


def run_smoke(log=print):
    """Смоук-прогон; True — провалов нет."""
    fails = 0
    tmp = Path(tempfile.mkdtemp(prefix="textools_smoke_"))
    try:
        copy = tmp / "vault"
        shutil.copytree(VAULT, copy)
        copy_reg = copy / "registry.yaml"
        copy_md = copy / "Сцены" / "01 начало.md"
        tmp_docx = tmp / "smoke_export.docx"

        log(f"Смоук CLI: полигон {VAULT.name}, "
            "read-only по оригиналу, пишущие — по копии.")

        def ro_fill(spec):
            return [a.replace("{vault}", str(VAULT))
                    .replace("{reg}", str(REGISTRY))
                    .replace("{vault_md}", str(copy_md))
                    .replace("{tmp_docx}", str(tmp_docx))
                    for a in spec]

        def wr_fill(spec):
            return [a.replace("{copy}", str(copy))
                    .replace("{copy_reg}", str(copy_reg))
                    .replace("{cand}", str(CANDIDATES))
                    for a in spec]

        fails += _report("READ-ONLY (по оригиналу полигона)",
                         READ_ONLY, log, ro_fill)
        fails += _report("WRITE (по временной копии)", WRITE, log, wr_fill)

        log("=" * 72)
        log("Пропущены намеренно: "
            + "; ".join(f"{n} — {why}" for n, why in SKIP))
        if fails:
            log(f"ИТОГ: {fails} провал(ов) — см. пометки ПРОВАЛ выше.")
        else:
            log("ИТОГ: все команды отработали штатно (коды 0/1).")
        return fails == 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(opts=None):
    ap = argparse.ArgumentParser(
        description="смоук-прогон всех CLI-подкоманд на полигоне "
                    "(test/demo_garbage/vault); read-only — по оригиналу, "
                    "пишущие — по временной копии")
    ap.parse_args(opts if opts is not None else [])
    return 0 if run_smoke() else 1


if __name__ == "__main__":  # прямой запуск: python tools/cli_smoke.py
    sys.exit(main())
