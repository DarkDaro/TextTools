"""
updater — обновление TextTools с GitHub (21.11, просьба владельца:
«чтобы можно было обновить из гуи и из батника, и с гитхаба всё само
докачивает и обновляет»).

Единственный сетевой модуль приложения — и то по явной команде:
  python textools.py update             — только проверка (как --check);
  python textools.py update --apply     — докачать и применить.

Офлайн-принцип не нарушается: без этой команды сеть не трогается
вообще, ни при запуске GUI, ни при запуске других инструментов.

Два пути обновления — тот же выбор, что у патника update.bat:
  1. git-копия (есть папка .git и git в PATH): git fetch + merge
     --ff-only. Локальные правки мешают — автоматически переходим
     на zip, ничего не ломая.
  2. zip-копия: архив main.zip с codeload.github.com, файлы копируются
     поверх без удаления, личные данные не трогаются (gui_config.json,
     logs/, reports/, stop.flag). Тот же набор исключений, что у
     tools/update_from_zip.ps1, только средствами Python.

После обновления GUI надо перезапустить — запущенный интерфейс
продолжает работать старым кодом из памяти.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REPO = "DarkDaro/TextTools"
API_URL = f"https://api.github.com/repos/{REPO}/commits/main"
RAW_URL = f"https://raw.githubusercontent.com/{REPO}/main/textools.py"
ZIP_URL = f"https://codeload.github.com/{REPO}/zip/refs/heads/main"
HEADERS = {"User-Agent": "TextTools-updater"}
TIMEOUT = 20
# архив main.zip меньше этого размера — сеть или прокси режут загрузку
MIN_ZIP_BYTES = 100_000

# папки и файлы, которые zip-обновление не трогает (личные данные и
# рабочий мусор); .git нужен git-копиям, logs/reports — журнал и отчёты
SKIP_DIRS = {".git", "__pycache__", "logs", "reports"}
SKIP_FILES = {"gui_config.json", "stop.flag", "gui_config.json.tmp"}

VER_RE = re.compile(r'__version__\s*=\s*"(.+?)"')


# --- сеть: одна точка, которую удобно подменить в тестах -------------

def _fetch_bytes(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# --- локальное состояние ---------------------------------------------

def local_version(root=ROOT):
    """Версия из textools.py ("" — не удалось прочитать). Файл читаем
    текстом: import тянет модуль в кэш и живёт своей жизнью, а в
    exe-режиме файла рядом с root может не быть — тогда fallback на
    import."""
    p = root / "textools.py"
    try:
        if p.is_file():
            m = VER_RE.search(p.read_text(encoding="utf-8",
                                          errors="replace"))
            if m:
                return m.group(1)
    except Exception:
        pass
    try:
        sys.path.insert(0, str(root))
        import textools
        return str(textools.__version__)
    except Exception:
        return ""


def local_commit(root=ROOT):
    """Первые 10 знаков SHA HEAD git-копии; "" — нет .git или git умер.
    10 знаков — столько же даёт ls-remote, чтобы сравнение было честным."""
    if not (root / ".git").is_dir():
        return ""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root, capture_output=True, text=True, timeout=30)
        return out.stdout.strip()[:10] if out.returncode == 0 else ""
    except Exception:
        return ""


def remote_info(fetch=_fetch_bytes):
    """(версия, sha, дата) с GitHub; чего-то может не быть — ""."""
    version, sha, date = "", "", ""
    try:
        doc = json.loads(fetch(API_URL).decode("utf-8"))
        sha = str(doc.get("sha", ""))[:10]
        date = str(doc.get("commit", {}).get("author", {}).get("date", ""))
    except Exception:
        pass
    try:
        m = VER_RE.search(fetch(RAW_URL).decode("utf-8", "replace"))
        if m:
            version = m.group(1)
    except Exception:
        pass
    return version, sha, date


def remote_commit(root=ROOT):
    """SHA main на GitHub через git ls-remote — обычный git-протокол,
    без лимитов API (у api.github.com часовой лимит, и без токена он
    нередко исчерпан). "" — нет git или нет сети."""
    if not shutil.which("git"):
        return ""
    try:
        r = subprocess.run(
            ["git", "ls-remote", f"https://github.com/{REPO}.git", "main"],
            cwd=root, capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            lines = r.stdout.strip().splitlines()
            return lines[0].split()[0][:10] if lines else ""
    except Exception:
        pass
    return ""


def _fmt_date(iso):
    """'2026-11-20T18:40:00Z' -> '20.11.2026'; непонятное — как было."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso)
    return f"{m.group(3)}.{m.group(2)}.{m.group(1)}" if m else (iso or "?")


# --- проверка ---------------------------------------------------------

def run_check(root=ROOT, fetch=_fetch_bytes, log=print):
    """Сверка локальной версии и коммита с GitHub. True — связь была."""
    lv, lc = local_version(root), local_commit(root)
    log(f"Локальная версия: {lv or '?'}"
        + (f" (git {lc})" if lc else " (копия без git)"))
    try:
        rv, rs_api, rd = remote_info(fetch)
    except Exception as e:
        rv, rs_api, rd = "", "", ""
        log(f"GitHub по HTTPS недоступен: {e}")
    # git-копии: надёжный SHA через ls-remote, API часто в лимите
    rs = remote_commit(root) or rs_api
    if not rv and not rs:
        log("GitHub недоступен: проверьте интернет и запустите "
            "обновление ещё раз.")
        return False
    parts = []
    if rv:
        parts.append(f"версия {rv}")
    if rs:
        parts.append(f"коммит {rs} от {_fmt_date(rd)}"
                     if rd else f"коммит {rs}")
    log("На GitHub: " + ", ".join(parts))

    newer = False
    if lc and rs:
        newer = rs != lc
    elif rv and lv:
        newer = rv != lv
    else:
        log("Сверить нечего: нет ни пары версий, ни пары коммитов.")
        return True
    if newer:
        log("Обновление доступно: ДА. Запустите «Обновить сейчас» "
            "(или python textools.py update --apply).")
    else:
        log("Обновление доступно: НЕТ — у вас уже последняя версия.")
    return True


# --- применение: git --------------------------------------------------

def apply_git(root=ROOT, log=print):
    """git fetch + merge --ff-only. True — обновилось (или уже свежее)."""
    try:
        r = subprocess.run(
            ["git", "fetch", "origin", "main"],
            cwd=root, capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            log("git fetch не прошёл: " + (r.stderr or "").strip()[:300])
            return False
        r = subprocess.run(
            ["git", "merge", "--ff-only", "origin/main"],
            cwd=root, capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            log("git merge не прошёл (обычно — локальные правки): "
                + (r.stderr or "").strip()[:300])
            return False
        log(f"Git-обновление готово: HEAD теперь "
            f"{local_commit(root) or '?'}")
        return True
    except Exception as e:
        log(f"git не сработал: {e}")
        return False


# --- применение: zip --------------------------------------------------

def _copy_tree(src, dst, log):
    """Копирование поверх без удаления: личные данные и мусор не трогаем."""
    files, skipped = 0, 0
    for p in src.rglob("*"):
        rel = p.relative_to(src)
        if SKIP_DIRS & set(rel.parts):
            continue
        if p.is_dir():
            (dst / rel).mkdir(parents=True, exist_ok=True)
            continue
        if not p.is_file():
            continue
        if p.name in SKIP_FILES:
            skipped += 1
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
        files += 1
    log(f"Скопировано файлов: {files}; пропущено личных: {skipped}")
    return files


def apply_zip(root=ROOT, fetch=_fetch_bytes, log=print):
    """Zip-путь: скачать main.zip, распаковать, скопировать поверх,
    сверить версию. True — обновилось."""
    tmp = Path(tempfile.mkdtemp(prefix="TextTools_upd_"))
    zpath = tmp / "main.zip"
    try:
        log("Скачиваю архив с GitHub (может занять минуту)...")
        data = fetch(ZIP_URL, timeout=300)
        if len(data) < MIN_ZIP_BYTES:
            log(f"Архив подозрительно мал ({len(data)} байт) — "
                "сеть или прокси режут загрузку.")
            return False
        zpath.write_bytes(data)
        log("Распаковываю...")
        with zipfile.ZipFile(zpath) as z:
            z.extractall(tmp)
        src = tmp / "TextTools-main"
        if not src.is_dir():
            log("В архиве нет папки TextTools-main.")
            return False
        log("Копирую файлы поверх (личные данные не трогаю)...")
        _copy_tree(src, root, log)
        m_src = VER_RE.search((src / "textools.py").read_text("utf-8"))
        m_dst = VER_RE.search((root / "textools.py").read_text("utf-8"))
        v_src = m_src.group(1) if m_src else "?"
        v_dst = m_dst.group(1) if m_dst else "?"
        if v_dst != v_src:
            log(f"Версия в папке ({v_dst}) не совпала с архивом ({v_src}) — "
                "файл занят или копирование не прошло.")
            return False
        log(f"Файлы обновлены и проверены: версия {v_dst} на месте.")
        return True
    except Exception as e:
        log(f"Zip-обновление не удалось: {e}")
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_apply(root=ROOT, fetch=_fetch_bytes, log=print):
    """Обновить: git-путь, при провале — zip. True — успех."""
    before = local_version(root) or "?"
    log(f"Обновление с GitHub. Версия до: {before}.")
    ok = False
    if (root / ".git").is_dir() and shutil.which("git"):
        log("Путь 1: git (fetch + merge --ff-only)...")
        ok = apply_git(root, log)
        if not ok:
            log("Перехожу на путь 2: zip-архив...")
            ok = apply_zip(root, fetch, log)
    else:
        log("Это не git-копия или git не найден — путь 2: zip-архив...")
        ok = apply_zip(root, fetch, log)
    after = local_version(root) or "?"
    if ok:
        log(f"Готово. Версия: {before} -> {after}. "
            "Перезапустите TextTools, чтобы новый код заработал.")
    else:
        log("Обновление НЕ удалось. Проверьте интернет и попробуйте "
            "ещё раз; для zip-копий подойдёт и update.bat.")
    return ok


def main(opts=None):
    ap = argparse.ArgumentParser(
        description="обновление с GitHub: --check (по умолчанию) "
                    "или --apply. Сеть трогается только этой командой.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--apply", action="store_true",
                   help="скачать и применить обновление")
    g.add_argument("--check", action="store_true",
                   help="только проверить (по умолчанию)")
    args = ap.parse_args(opts if opts is not None else [])
    log = print
    if args.apply:
        return 0 if run_apply(log=log) else 1
    return 0 if run_check(log=log) else 1


if __name__ == "__main__":  # прямой запуск: python tools/updater.py
    sys.exit(main())
