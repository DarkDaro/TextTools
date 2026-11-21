# -*- coding: utf-8 -*-
"""
Юнит-тесты tools/updater: обновление с GitHub без реальной сети.
Сеть подменяется фейковым fetch; zip-путь проверяется на настоящем
архиве, собранном в памяти.

Запуск: python -m pytest test/test_updater_units.py
"""
import io
import json
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools import updater  # noqa: E402


def _capture():
    out = []

    def log(msg):
        out.append(str(msg))
    return log, out


# --- мелкие функции ---------------------------------------------------

def test_fmt_date():
    assert updater._fmt_date("2026-11-20T18:40:00Z") == "20.11.2026"
    assert updater._fmt_date("") == "?"
    assert updater._fmt_date("мусор") == "мусор"


def test_local_version_and_commit():
    import textools
    assert updater.local_version() == textools.__version__
    c = updater.local_commit()
    assert c == "" or (len(c) == 10 and c.islower())


def test_local_commit_not_git(tmp_path):
    assert updater.local_commit(tmp_path) == ""


def test_version_regex():
    m = updater.VER_RE.search('__version__ = "1.2.3"\n')
    assert m.group(1) == "1.2.3"


# --- проверка (check) -------------------------------------------------

def _fake_fetch(api_sha="a" * 40, version=None, date="2026-11-20T18:40:00Z",
                api_ok=True, raw_ok=True):
    def fetch(url, timeout=updater.TIMEOUT):
        if url == updater.API_URL:
            if not api_ok:
                raise OSError("api недоступен")
            return json.dumps(
                {"sha": api_sha,
                 "commit": {"author": {"date": date}}}).encode()
        if url == updater.RAW_URL:
            if not raw_ok:
                raise OSError("raw недоступен")
            v = version or "1.8.5"
            return f'__version__ = "{v}"\n'.encode()
        raise OSError(f"неизвестный адрес: {url}")
    return fetch


def test_check_same_version(monkeypatch, capsys):
    monkeypatch.setattr(updater, "remote_commit", lambda root="": "b" * 10)
    monkeypatch.setattr(updater, "local_commit", lambda root="": "b" * 10)
    assert updater.run_check(fetch=_fake_fetch()) is True
    text = capsys.readouterr().out
    assert "НЕТ" in text


def test_check_update_available_by_commit(monkeypatch, capsys):
    monkeypatch.setattr(updater, "remote_commit", lambda root="": "c" * 10)
    monkeypatch.setattr(updater, "local_commit", lambda root="": "b" * 10)
    assert updater.run_check(fetch=_fake_fetch()) is True
    assert "ДА" in capsys.readouterr().out


def test_check_update_available_by_version(monkeypatch, capsys):
    monkeypatch.setattr(updater, "remote_commit", lambda root="": "")
    monkeypatch.setattr(updater, "local_commit", lambda root="": "")
    # локальную версию в test-корне не подменяем: сравнение по версии
    # сработает, потому что на GitHub «другая» версия
    assert updater.run_check(fetch=_fake_fetch(version="9.9.9")) is True
    assert "ДА" in capsys.readouterr().out


def test_check_network_dead(monkeypatch, capsys):
    def fetch(url, timeout=updater.TIMEOUT):
        raise OSError("нет сети")
    monkeypatch.setattr(updater, "remote_commit", lambda root="": "")
    assert updater.run_check(fetch=fetch) is False
    assert "недоступен" in capsys.readouterr().out


def test_check_api_dead_but_raw_alive(monkeypatch, capsys):
    # API часто в лимите: версия с raw спасает проверку
    import textools
    monkeypatch.setattr(updater, "remote_commit", lambda root="": "")
    monkeypatch.setattr(updater, "local_commit", lambda root="": "")
    assert updater.run_check(
        fetch=_fake_fetch(api_ok=False,
                          version=textools.__version__)) is True
    assert "НЕТ" in capsys.readouterr().out


# --- применение: zip --------------------------------------------------

def _zip_bytes(entries, top="TextTools-main"):
    """Архив в памяти; набиваем до MIN_ZIP_BYTES, чтобы сработала
    настоящая проверка размера (в тестах хотим честный путь)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in entries.items():
            z.writestr(f"{top}/{name}", data)
        z.writestr(f"{top}/_pad.txt", " " * (updater.MIN_ZIP_BYTES + 10_000))
    return buf.getvalue()


def test_apply_zip_updates_files(tmp_path, capsys):
    log, out = _capture()
    (tmp_path / "textools.py").write_text(
        '__version__ = "1.8.5"\n', encoding="utf-8")
    (tmp_path / "gui_config.json").write_text('{"ui_lang": "ru"}',
                                              encoding="utf-8")
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "history.log").write_text("журнал", encoding="utf-8")
    zdata = _zip_bytes({
        "textools.py": '__version__ = "9.9.9"\n',
        "core/newmod.py": "# новый модуль\n",
        "gui_config.json": '{"чужое": true}',
        "logs/history.log": "перезаписать меня нельзя",
        "stop.flag": "stop",
    })
    fetch = lambda url, timeout=updater.TIMEOUT: zdata  # noqa: E731
    assert updater.apply_zip(root=tmp_path, fetch=fetch, log=log) is True
    text = "\n".join(out)
    assert "9.9.9" in text
    # новый файл приехал
    assert (tmp_path / "core" / "newmod.py").exists()
    # личные данные не тронуты
    assert json.loads((tmp_path / "gui_config.json").read_text(
        encoding="utf-8")) == {"ui_lang": "ru"}
    assert (logs / "history.log").read_text(encoding="utf-8") == "журнал"
    assert not (tmp_path / "stop.flag").exists()
    # версия в папке стала версией из архива
    assert updater.local_version(tmp_path) == "9.9.9"


def test_apply_zip_bad_size(tmp_path, capsys):
    log, out = _capture()
    (tmp_path / "textools.py").write_text(
        '__version__ = "1.8.5"\n', encoding="utf-8")
    fetch = lambda url, timeout=updater.TIMEOUT: "крошка".encode()  # noqa: E731
    assert updater.apply_zip(root=tmp_path, fetch=fetch, log=log) is False
    assert "мал" in "\n".join(out)
    # старый файл не побит
    assert updater.local_version(tmp_path) == "1.8.5"


def test_apply_zip_broken_archive(tmp_path):
    log, _ = _capture()
    (tmp_path / "textools.py").write_text(
        '__version__ = "1.8.5"\n', encoding="utf-8")
    # больше MIN_ZIP_BYTES, но не zip
    fetch = lambda url, timeout=updater.TIMEOUT: b"x" * 200_000  # noqa: E731
    assert updater.apply_zip(root=tmp_path, fetch=fetch, log=log) is False
    assert updater.local_version(tmp_path) == "1.8.5"


def test_apply_zip_without_topdir(tmp_path):
    log, out = _capture()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("random/readme.txt", "не тот архив")
        z.writestr("random/pad.txt", " " * (updater.MIN_ZIP_BYTES + 10_000))
    fetch = lambda url, timeout=updater.TIMEOUT: buf.getvalue()  # noqa: E731
    assert updater.apply_zip(root=tmp_path, fetch=fetch, log=log) is False
    assert "TextTools-main" in "\n".join(out)


# --- применение: общий путь -------------------------------------------

def test_run_apply_zip_copy(tmp_path, monkeypatch):
    # не git-копия → сразу zip-путь; фейковый архив «обновляет»
    zdata = _zip_bytes({"textools.py": '__version__ = "9.9.9"\n'})
    fetch = lambda url, timeout=updater.TIMEOUT: zdata  # noqa: E731
    (tmp_path / "textools.py").write_text(
        '__version__ = "1.8.5"\n', encoding="utf-8")
    log, out = _capture()
    assert updater.run_apply(root=tmp_path, fetch=fetch, log=log) is True
    text = "\n".join(out)
    assert "zip-архив" in text
    assert "1.8.5 -> 9.9.9" in text


def test_run_apply_git_fails_falls_back(tmp_path, monkeypatch):
    # git-папка есть, но apply_git возвращает провал → переходим на zip
    (tmp_path / ".git").mkdir()
    zdata = _zip_bytes({"textools.py": '__version__ = "9.9.9"\n'})
    fetch = lambda url, timeout=updater.TIMEOUT: zdata  # noqa: E731
    (tmp_path / "textools.py").write_text(
        '__version__ = "1.8.5"\n', encoding="utf-8")
    monkeypatch.setattr(updater, "apply_git", lambda *a, **k: False)
    log, out = _capture()
    assert updater.run_apply(root=tmp_path, fetch=fetch, log=log) is True
    assert "путь 2" in "\n".join(out)


# --- CLI --------------------------------------------------------------

def test_main_check_wraps_run_check(monkeypatch):
    monkeypatch.setattr(updater, "run_check",
                        lambda log=print, **k: True)
    assert updater.main(["--check"]) == 0


def test_main_check_failure_code(monkeypatch):
    monkeypatch.setattr(updater, "run_check", lambda log=print, **k: False)
    assert updater.main(["--check"]) == 1


def test_main_apply_wraps_run_apply(monkeypatch):
    called = {}

    def fake_apply(log=print, **k):
        called["x"] = True
        return True
    monkeypatch.setattr(updater, "run_apply", fake_apply)
    assert updater.main(["--apply"]) == 0
    assert called.get("x")


def test_main_default_is_check(monkeypatch):
    seen = {}

    def fake_check(log=print, **k):
        seen["check"] = True
        return True
    monkeypatch.setattr(updater, "run_check", fake_check)
    assert updater.main([]) == 0
    assert seen.get("check")
