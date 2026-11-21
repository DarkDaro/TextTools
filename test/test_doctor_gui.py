# TD-05: живая проверка окна (doctor --gui) и разбор диагностики selftest.
# Юнит-тесты разбора — без дисплея; интеграционный — только при DISPLAY
# (в CI без дисплея пропускается, как договорились в TD-03).
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.app_check import EXPECTED_TABS, _gui_selftest  # noqa: E402


class _FakeRun:
    """Подмена subprocess.run для _gui_selftest."""

    def __init__(self, stdout="", stderr="", returncode=0,
                 exc=None):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self._exc = exc

    def __call__(self, *a, **kw):
        if self._exc is not None:
            raise self._exc
        return self


def _payload(ok=True, version="1.9.1", tab_count=None, error=""):
    doc = {"ok": ok, "version": version, "py": "3.12.0", "ctk": "6.0.0",
           "tabs": ["Писателям"], "tab_count": EXPECTED_TABS,
           "error": error}
    if tab_count is not None:
        doc["tab_count"] = tab_count
    return "SELFTEST " + json.dumps(doc, ensure_ascii=False)


def test_selftest_ok(monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        _FakeRun(stdout=_payload() + "\n"))
    status, detail = _gui_selftest()
    assert status == "ok"
    assert "вкладок 8" in detail


def test_selftest_no_json(monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        _FakeRun(stdout="что-то не то\n", returncode=1))
    status, detail = _gui_selftest()
    assert status == "fail"
    assert "без диагностики" in detail


def test_selftest_broken_window(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        _FakeRun(stdout=_payload(ok=False, error="RuntimeError: бум") + "\n"))
    status, detail = _gui_selftest()
    assert status == "fail"
    assert "RuntimeError" in detail


def test_selftest_version_mismatch(monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        _FakeRun(stdout=_payload(version="0.0.1") + "\n"))
    status, detail = _gui_selftest()
    assert status == "fail"
    assert "версии ядра" in detail


def test_selftest_tab_lost(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        _FakeRun(stdout=_payload(tab_count=EXPECTED_TABS - 1) + "\n"))
    status, detail = _gui_selftest()
    assert status == "fail"
    assert "вкладка потерялась" in detail


def test_selftest_timeout(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        _FakeRun(exc=subprocess.TimeoutExpired(cmd="gui", timeout=120)))
    status, detail = _gui_selftest()
    assert status == "fail"
    assert "не отстроилось" in detail


def test_selftest_spawn_fail(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        _FakeRun(exc=OSError("нет питона")))
    status, detail = _gui_selftest()
    assert status == "fail"
    assert "запуск не удался" in detail


@pytest.mark.skipif(not os.environ.get("DISPLAY"),
                    reason="живое окно: нужен дисплей (локально, не CI)")
def test_doctor_gui_live():
    """Полный doctor --gui на живом окне: 0 провалов."""
    from tools import app_check
    root = Path(__file__).resolve().parent.parent
    r = subprocess.run(
        [sys.executable, str(root / "textools.py"), "doctor", "--gui"],
        capture_output=True, text=True, timeout=180, cwd=str(root))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "живое окно" in r.stdout
