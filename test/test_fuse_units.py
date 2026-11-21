# -*- coding: utf-8 -*-
"""
Юнит-тесты core/fuse: предохранители от зависаний (лимит размера
файла, бюджет времени, стоп-файл), цепочка источников значений и
интеграция со scan_vault.

Запуск: python -m pytest test/test_fuse_units.py
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from core import fuse  # noqa: E402
from core.fuse import Fuse  # noqa: E402
from core.vault_scanner import scan_vault  # noqa: E402


def _quiet():
    return lambda *_: None


# --- цепочка источников ------------------------------------------------

def test_defaults(monkeypatch):
    monkeypatch.delenv("TEXTOOLS_LANG", raising=False)
    f = Fuse(log=_quiet())
    assert f.max_bytes == fuse.DEFAULT_MAX_MB * fuse.MB
    assert f.deadline is not None


def test_explicit_arg_wins(monkeypatch, tmp_path):
    monkeypatch.setattr(fuse, "_from_config",
                        lambda key: 8 if key == "fuse.max_mb" else None)
    f = Fuse(max_mb=1, max_min=0, log=_quiet())
    assert f.max_bytes == fuse.MB
    assert f.deadline is None  # 0 = выключен


def test_zero_disables(monkeypatch):
    f = Fuse(max_mb=0, max_min=0, log=_quiet())
    assert f.max_bytes == 0
    assert f.deadline is None


def test_config_value_used(monkeypatch):
    monkeypatch.setattr(fuse, "_from_config",
                        lambda key: {"fuse.max_mb": 8,
                                     "fuse.max_min": 3}.get(key))
    f = Fuse(log=_quiet())
    assert f.max_bytes == 8 * fuse.MB
    assert f.deadline is not None


def test_bad_config_degrades(monkeypatch):
    monkeypatch.setattr(fuse, "_from_config", lambda key: None)
    f = Fuse(log=_quiet())
    assert f.max_bytes == fuse.DEFAULT_MAX_MB * fuse.MB


# --- размер ------------------------------------------------------------

def test_allow_file_skips_big(tmp_path):
    big = tmp_path / "big.md"
    big.write_bytes(b"x" * (fuse.MB + 100_000))
    f = Fuse(max_mb=1, max_min=0, log=_quiet())
    assert f.allow_file(big) is False
    assert len(f.skipped) == 1
    assert "1.1 МБ" in f.summary()[0]


def test_allow_file_small_ok(tmp_path):
    small = tmp_path / "s.md"
    small.write_text("обычная заметка", encoding="utf-8")
    f = Fuse(max_mb=1, max_min=0, log=_quiet())
    assert f.allow_file(small) is True
    assert f.skipped == []


def test_limit_zero_means_unlimited(tmp_path):
    big = tmp_path / "big.md"
    big.write_bytes(b"x" * 300)  # мелкий файл, но лимит 0 → без проверок
    f = Fuse(max_mb=0, max_min=0, log=_quiet())
    assert f.allow_file(big) is True


# --- время и стоп ------------------------------------------------------

def test_deadline_expires():
    f = Fuse(max_mb=0, max_min=0.00001, log=_quiet())
    time.sleep(0.01)
    assert f.check() is False
    assert "лимит времени" in f.stopped_by


def test_stop_file(tmp_path):
    flag = tmp_path / "stop.flag"
    f = Fuse(max_mb=0, max_min=0, log=_quiet(), stop_file=flag)
    assert f.check() is True
    flag.write_text("stop", encoding="utf-8")
    assert f.check() is False
    assert "стоп-файл" in f.stopped_by


def test_summary_silent_when_nothing_happened(tmp_path):
    f = Fuse(max_mb=1, max_min=0, log=_quiet())
    assert f.summary() == []


# --- scan_vault --------------------------------------------------------

def _vault_with_big(tmp_path):
    (tmp_path / "a.md").write_text("# A\nтекст", encoding="utf-8")
    big = tmp_path / "big.md"
    big.write_bytes(b"x" * (fuse.MB + 100_000))
    (tmp_path / "b.md").write_text("# B\n[[a]]", encoding="utf-8")
    return big


def test_scan_vault_skips_big_by_own_fuse(tmp_path, capsys, monkeypatch):
    # штатный Fuse конструируется с константой по умолчанию — для теста
    # подменяем её на 1 МБ, чтобы сработала настоящая ветка
    monkeypatch.setattr(fuse, "DEFAULT_MAX_MB", 1)
    big = _vault_with_big(tmp_path)
    notes, _bn, _rp, _at = scan_vault(tmp_path)
    names = {n.path.name for n in notes}
    assert "a.md" in names and "b.md" in names and big.name not in names
    out = capsys.readouterr().out
    assert "Предохранитель" in out and big.name in out


def test_scan_vault_with_passed_fuse_is_quiet(tmp_path, capsys):
    _vault_with_big(tmp_path)
    f = Fuse(max_mb=1, max_min=0, log=_quiet())
    scan_vault(tmp_path, fuse=f)
    assert capsys.readouterr().out == ""
    assert len(f.skipped) == 1


def test_scan_vault_stop_file_between_files(tmp_path, capsys, monkeypatch):
    (tmp_path / "a.md").write_text("# A", encoding="utf-8")
    (tmp_path / "b.md").write_text("# B", encoding="utf-8")
    (tmp_path / "stop.flag").write_text("stop", encoding="utf-8")
    # штатный Fuse смотрит на stop.flag в корне проекта — в тесте
    # направляем его во временную папку
    monkeypatch.setattr(fuse, "STOP_FILE", tmp_path / "stop.flag")
    notes, _bn, _rp, _at = scan_vault(tmp_path)
    out = capsys.readouterr().out
    assert "стоп-файл" in out


def test_scan_vault_plain_works(tmp_path):
    (tmp_path / "a.md").write_text("# A\nпривет", encoding="utf-8")
    notes, bn, rp, _at = scan_vault(tmp_path)
    assert len(notes) == 1
    assert bn == {"a"}
    assert rp == {"a"}
