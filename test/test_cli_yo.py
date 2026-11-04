"""
Тесты CLI-команды yo (textools.py): проводка yo_audit через подкоманду.

05.11: ё/е-аудит был доступен из GUI и прямым вызовом
tools/yo_audit.py, но в textools.py подкоманды не было — по --help
команду не найти. Чанк BACKLOG №1.

Запуск:  python -m pytest test/test_cli_yo.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _cli(*args):
    return subprocess.run(
        [sys.executable, "textools.py", *args],
        cwd=ROOT, capture_output=True, text=True)


def test_yo_visible_in_help():
    r = _cli("--help")
    assert r.returncode == 0
    # команда видна в справочнике — с этого всё началось
    assert "yo" in r.stdout


def test_yo_finds_and_reports(tmp_path):
    f = tmp_path / "глава.md"
    f.write_text("Черный шепот объял комнату.\n", encoding="utf-8")
    r = _cli("yo", "--input", str(f))
    assert r.returncode == 0
    # словарные пары: черный->чёрный, шепот->шёпот
    assert "черный" in r.stdout and "чёрный" in r.stdout
    assert "шепот" in r.stdout and "шёпот" in r.stdout


def test_yo_review_lines_and_out(tmp_path):
    f = tmp_path / "глава.md"
    f.write_text("Он шел мимо. Объем тома был велик.\n", encoding="utf-8")
    out = tmp_path / "rep" / "yo.md"
    r = _cli("yo", "--input", str(f), "--review", "--out", str(out))
    assert r.returncode == 0
    # витрина: YO-строки для GUI/скриптов
    assert r.stdout.count("YO\t") >= 2
    rep = out.read_text(encoding="utf-8")
    assert "шел" in rep and "шёл" in rep
    assert "объем" in rep and "объём" in rep


def test_yo_json_not_supported_but_dict_is(tmp_path):
    # свой словарь полностью заменяет встроенный (как в доке yo_audit)
    f = tmp_path / "глава.md"
    f.write_text("Мел лежал на полу.\n", encoding="utf-8")
    d = tmp_path / "my_dict.yaml"
    d.write_text("омографы:\n  - мел|мёл\nсловарные: []\n",
                 encoding="utf-8")
    r = _cli("yo", "--input", str(f), "--dict", str(d), "--out", "-")
    assert r.returncode == 0
    assert "мел" in r.stdout and "мёл" in r.stdout
