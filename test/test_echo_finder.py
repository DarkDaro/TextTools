"""
Тесты «эхо-фраз» (echo_finder): повторы конструкций между РАЗНЫМИ
файлами — внутри файла ловит style-report, между файлами до сих пор
не ловил никто (BACKLOG №6).

Запуск:  python -m pytest test/test_echo_finder.py
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import echo_finder

ECHO = "Мир сжался до точки, и стало тихо."


def _vault(tmp_path):
    (tmp_path / "глава1.md").write_text(
        f"# Глава 1\n\n{ECHO} Она открыла глаза.\n", encoding="utf-8")
    (tmp_path / "глава2.md").write_text(
        f"# Глава 2\n\nОн молчал. {ECHO}\n", encoding="utf-8")
    (tmp_path / "глава3.md").write_text(
        "# Глава 3\n\nСовсем другой текст про ветер и дорогу.\n",
        encoding="utf-8")


def test_finds_cross_file_echo(tmp_path):
    _vault(tmp_path)
    items = echo_finder.find_echo(str(tmp_path), n=3, min_files=2)
    grams = {it["ngram"] for it in items}
    assert "мир сжался до" in grams
    assert "сжался до точки" in grams
    hit = next(it for it in items if it["ngram"] == "мир сжался до")
    assert hit["files"] == 2 and hit["count"] >= 2
    assert "глава1" in hit["example"]["file"]


def test_single_file_repeats_not_enough(tmp_path):
    # повтор в одном файле — не эхо (это зона style-report)
    (tmp_path / "глава.md").write_text(
        f"{ECHO}\n\nИ снова: {ECHO}\n", encoding="utf-8")
    items = echo_finder.find_echo(str(tmp_path), n=3, min_files=2)
    assert not any("сжался" in it["ngram"] for it in items)


def test_registry_names_excluded(tmp_path):
    reg = tmp_path / "реестр.yaml"
    reg.write_text(
        "- имя: Мира\n  формы: [Мирры, Мире]\n", encoding="utf-8")
    (tmp_path / "а.md").write_text(
        "Мира смотрела в окно и ждала.\n", encoding="utf-8")
    (tmp_path / "б.md").write_text(
        "Мира смотрела в окно и вздыхала.\n", encoding="utf-8")
    items = echo_finder.find_echo(str(tmp_path), n=3, min_files=2,
                                  name_words=echo_finder.load_name_words(reg))
    assert not any("мира" in it["ngram"] for it in items)


def test_stopword_ngrams_skipped(tmp_path):
    # «как бы что» — только служебные слова, конструкции не образует
    (tmp_path / "а.md").write_text("Как бы что это было.\n",
                                   encoding="utf-8")
    (tmp_path / "б.md").write_text("Как бы что сказать.\n",
                                   encoding="utf-8")
    items = echo_finder.find_echo(str(tmp_path), n=3, min_files=2)
    assert not any(it["ngram"] == "как бы что" for it in items)


def test_yo_ignored_ngram(tmp_path):
    # ё=е: «пошёл» и «пошел» — одна конструкция
    (tmp_path / "а.md").write_text("Он пошёл в сторону реки.\n",
                                   encoding="utf-8")
    (tmp_path / "б.md").write_text("Он пошел в сторону леса.\n",
                                   encoding="utf-8")
    items = echo_finder.find_echo(str(tmp_path), n=3, min_files=2)
    assert any(it["ngram"] == "он пошел в" for it in items)


def test_top_cuts_list(tmp_path):
    _vault(tmp_path)
    items = echo_finder.find_echo(str(tmp_path), n=3, min_files=2, top=1)
    assert len(items) == 1


def test_run_report_and_json(tmp_path):
    _vault(tmp_path)
    out = tmp_path / "эхо.md"
    j = tmp_path / "эхо.json"
    rc = echo_finder.run(str(tmp_path), out=str(out), json_out=str(j))
    assert rc == 1  # находки есть
    text = out.read_text(encoding="utf-8")
    assert "мир сжался до" in text
    data = json.loads(j.read_text(encoding="utf-8"))
    assert data["tool"] == "echo" and data["total"] >= 2
    assert any(it["ngram"] == "сжался до точки" for it in data["items"])


def test_run_clean_returns_zero(tmp_path):
    (tmp_path / "одна.md").write_text("Текст без повторов вовсе.\n",
                                      encoding="utf-8")
    assert echo_finder.run(str(tmp_path)) == 0


def test_cli_wiring(tmp_path):
    _vault(tmp_path)
    r = subprocess.run(
        [sys.executable, "textools.py", "echo", "--input", str(tmp_path),
         "--out", "-"],
        cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 1
    assert "мир сжался до" in r.stdout


def test_cli_validates_n_and_min_files(tmp_path):
    r = subprocess.run(
        [sys.executable, "textools.py", "echo", "--input", str(tmp_path),
         "--n", "1"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 2
    r2 = subprocess.run(
        [sys.executable, "textools.py", "echo", "--input", str(tmp_path),
         "--min-files", "1"], cwd=ROOT, capture_output=True, text=True)
    assert r2.returncode == 2
    assert "style-report" in r2.stdout + r2.stderr


def test_cli_help_visible():
    r = subprocess.run(
        [sys.executable, "textools.py", "--help"],
        cwd=ROOT, capture_output=True, text=True)
    assert "echo" in r.stdout
