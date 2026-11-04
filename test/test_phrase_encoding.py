"""
Тесты кодировок в phrase-check: cp1251/koi8 заметки больше не молчат.

Поиск и витрина видят не-UTF8 файлы (автодетект, как в остальных
проверках); чистка их пропускает с явным предупреждением — запись
молча перекодировала бы файл в UTF-8.

Запуск:  python -m pytest test/test_phrase_encoding.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools import phrase_check


STAMP = "Стоит отметить, что текст идёт дальше."


def test_search_sees_cp1251(tmp_path, capsys):
    (tmp_path / "старая.md").write_text(STAMP, encoding="cp1251")
    code = phrase_check.run(str(tmp_path),
                            phrases=["стоит отметить, что"])
    out = capsys.readouterr().out
    assert "Файлов проверено: 1" in out  # раньше было 0 — файл молча шел мимо
    assert code == 1  # находки есть


def test_search_sees_koi8(tmp_path, capsys):
    (tmp_path / "старая.txt").write_text(STAMP, encoding="koi8-r")
    phrase_check.run(str(tmp_path), phrases=["стоит отметить, что"])
    assert "Файлов проверено: 1" in capsys.readouterr().out


def test_utf8_still_works(tmp_path, capsys):
    (tmp_path / "новая.md").write_text(STAMP, encoding="utf-8")
    phrase_check.run(str(tmp_path), phrases=["стоит отметить, что"])
    out = capsys.readouterr().out
    assert "Файлов проверено: 1" in out


def test_clean_skips_non_utf8_loudly(tmp_path, capsys):
    f = tmp_path / "старая.md"
    raw = STAMP.encode("cp1251")
    f.write_bytes(raw)
    phrase_check.clean(str(tmp_path), limit=None, dry_run=False, yes=True)
    out = capsys.readouterr().out
    assert "[ПРОПУЩЕН]" in out and "не UTF-8" in out
    assert f.read_bytes() == raw  # байты не тронуты — нет молчаливой перекодировки


def test_clean_still_cleans_utf8(tmp_path, capsys):
    f = tmp_path / "новая.md"
    f.write_text(STAMP, encoding="utf-8")
    phrase_check.clean(str(tmp_path), limit=None, dry_run=False, yes=True)
    out = capsys.readouterr().out
    assert "[ОЧИЩЕН]" in out
    assert "стоит отметить, что" not in f.read_text(encoding="utf-8").lower()
