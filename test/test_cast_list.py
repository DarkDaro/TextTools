"""
Тесты cast_list (07.11): список персонажей без повторов, пары «Имя
Фамилия», ошибки в написании одного имени (Семён/Семен), текстовый лог.

Запуск:  python -m pytest test/test_cast_list.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools import cast_list

CHAPTER = ("Семён стоял у окна и молчал. Семён ждал ответа от Ивана, "
           "а Иван Петрович смотрел в книгу.\n"
           "Семен вздохнул. Мастер Кайдзо улыбнулся.\n")

CHAPTER2 = ("Иван Петрович кивнул. Семён и Семен — разные написания "
            "одного имени.\n")


def test_scan_text_counts_names():
    single, pairs = cast_list.scan_text(CHAPTER)
    assert single["Семён"] >= 2
    assert single["Семен"] == 1
    assert pairs["Иван Петрович"] == 1
    assert pairs["Мастер Кайдзо"] == 1


def test_run_writes_log_with_variants(tmp_path):
    (tmp_path / "глава1.md").write_text(CHAPTER, encoding="utf-8")
    (tmp_path / "глава2.md").write_text(CHAPTER2, encoding="utf-8")
    out = tmp_path / "cast.txt"
    rc = cast_list.run(str(tmp_path), out=str(out))
    assert rc == 0
    body = out.read_text(encoding="utf-8")
    assert "Семён — 3" in body          # 2 + 1
    assert "Семен — 2" in body          # 1 в главе1 + 1 в главе2
    assert "Иван Петрович" in body
    assert "пишется по-разному" in body
    assert "Семён (3) / Семен (2)" in body


def test_min_count_filter(tmp_path):
    (tmp_path / "глава.md").write_text(CHAPTER, encoding="utf-8")
    out = tmp_path / "cast.txt"
    cast_list.run(str(tmp_path), out=str(out), min_count=2)
    body = out.read_text(encoding="utf-8")
    assert "Семён — " in body
    assert "Семен — 1" not in body      # один раз — отфильтрован


def test_unreadable_input_returns_1(tmp_path):
    rc = cast_list.run(str(tmp_path / "пусто"))
    assert rc == 1
