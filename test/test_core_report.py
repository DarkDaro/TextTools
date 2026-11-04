"""
Тесты core.report: запись отчёта, создание родительских папок,
режим «--out -» (отчёт в stdout для конвейеров).

Запуск:  python -m pytest test/test_core_report.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from core.report import write_report


def test_writes_file(tmp_path):
    p = tmp_path / "отчёт.md"
    write_report(p, "текст отчёта")
    assert p.read_text(encoding="utf-8") == "текст отчёта"


def test_creates_parent_dirs(tmp_path):
    p = tmp_path / "reports" / "sub" / "отчёт.md"
    write_report(p, "данные")
    assert p.read_text(encoding="utf-8") == "данные"


def test_dash_prints_to_stdout(capsys):
    write_report("-", "в stdout\n")
    out = capsys.readouterr().out
    assert "в stdout" in out
    # файла «-» не создаётся
    assert not (Path.cwd() / "-").exists()


def test_dash_spaced_prints_to_stdout(capsys):
    # «-» с пробелами тоже считается stdout (устойчивость к опечаткам)
    write_report(" - ", "содержимое")
    assert "содержимое" in capsys.readouterr().out
