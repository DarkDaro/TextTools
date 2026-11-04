"""
Тесты плохого --input: пустой и несуществующий путь — понятная ошибка,
а не тихий прогон по текущей папке или «0 файлов, всё чисто».

Раньше Path('') превращался в '.' — integrity просканировал 205 файлов
репозитория, а чистки на несуществующем пути отчитывались «чисто».

Запуск:  python -m pytest test/test_bad_input.py
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from core.text_parser import check_root
from core import vault_scanner as vs
from tools import whitespace_clean, separator_clean, typography, integrity_check

MISSING = "нет_такой_папки_нигде"


def test_check_root_empty():
    for bad in ("", "   ", None):
        try:
            check_root(bad)
        except ValueError as e:
            assert "не указан" in str(e)
        else:
            raise AssertionError(f"check_root({bad!r}) не поднял ValueError")


def test_check_root_missing():
    try:
        check_root(MISSING)
    except ValueError as e:
        assert "не найден" in str(e)
    else:
        raise AssertionError("check_root не поднял ValueError")


def test_clean_collects_raise(tmp_path):
    # и пустой, и несуществующий путь — ошибка, а не скан cwd
    for bad in ("", str(tmp_path / MISSING)):
        for collect in (whitespace_clean.collect, separator_clean.collect,
                        typography.collect):
            try:
                collect(bad)
            except ValueError:
                pass
            else:
                raise AssertionError(f"{collect.__module__}.collect({bad!r}) "
                                     "не поднял ValueError")


def test_scan_vault_raises(tmp_path):
    try:
        vs.scan_vault(str(tmp_path / MISSING))
    except ValueError:
        pass
    else:
        raise AssertionError("scan_vault не поднял ValueError")


def test_integrity_run_raises(tmp_path):
    try:
        integrity_check.run(str(tmp_path / MISSING))
    except ValueError:
        pass
    else:
        raise AssertionError("integrity_check.run не поднял ValueError")


def test_cli_reports_error_code_2():
    # через реальный CLI: сообщение в stderr, код 2, stdout пуст
    for args in (["--input", MISSING], ["--input", ""]):
        p = subprocess.run(
            [sys.executable, str(HERE / "textools.py"), "integrity", *args],
            capture_output=True, text=True, cwd=HERE)
        assert p.returncode == 2, args
        assert "Ошибка" in p.stderr
        assert p.stdout == ""
