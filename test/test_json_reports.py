"""
Тесты --json у проверок: каждая проверка пишет машинно-читаемый отчёт
(файл или «-» в stdout), как раньше умел только cjk.

Запуск:  python -m pytest test/test_json_reports.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools import (orphan_finder, broken_links, merge_finder,
                   integrity_check, utf8_convert, phrase_check,
                   obsidian_check)
from core.report import write_json


def _load(tmp_path, name, runner):
    j = tmp_path / name
    runner(str(j))
    return json.loads(j.read_text(encoding="utf-8"))


def test_orphan_json(tmp_path):
    (tmp_path / "одиночка.md").write_text("без ссылок\n", encoding="utf-8")
    data = _load(tmp_path, "o.json",
                 lambda p: orphan_finder.run(str(tmp_path), json_out=p))
    assert data["tool"] == "orphan-finder"
    assert data["notes"] == 1
    assert data["orphans"] == ["одиночка.md"]


def test_broken_links_json(tmp_path):
    (tmp_path / "A.md").write_text("[[нет такой]]\n", encoding="utf-8")
    data = _load(tmp_path, "b.json",
                 lambda p: broken_links.run(str(tmp_path), json_out=p))
    assert data["broken_wiki"] == [
        {"file": "A.md", "target": "нет такой"}]
    assert data["broken_md"] == []


def test_merge_finder_json(tmp_path):
    text = "Слово " * 30
    (tmp_path / "x.md").write_text(text, encoding="utf-8")
    (tmp_path / "y.md").write_text(text, encoding="utf-8")
    data = _load(tmp_path, "m.json",
                 lambda p: merge_finder.run(str(tmp_path), json_out=p))
    assert len(data["dup_content"]) == 1
    assert sorted(data["dup_content"][0]["files"]) == ["x.md", "y.md"]


def test_integrity_json(tmp_path):
    (tmp_path / "пусто.md").write_text("", encoding="utf-8")
    data = _load(tmp_path, "i.json",
                 lambda p: integrity_check.run(str(tmp_path), json_out=p))
    assert data["files"] == 1
    assert data["problems"][0]["issue"] == "ПУСТОЙ ФАЙЛ"


def test_utf8_json(tmp_path):
    (tmp_path / "старый.txt").write_text("привет", encoding="cp1251")
    data = _load(tmp_path, "u.json",
                 lambda p: utf8_convert.run(str(tmp_path), json_out=p))
    assert data["scanned"] == 1
    assert data["non_utf8"][0]["fixed"] is False
    assert data["non_utf8"][0]["encoding"]


def test_phrase_json(tmp_path):
    (tmp_path / "штампы.md").write_text(
        "Стоит отметить, что текст.", encoding="utf-8")
    data = _load(tmp_path, "p.json",
                 lambda p: phrase_check.run(str(tmp_path), json_out=p))
    assert data["total"] >= 1
    assert any("стоит отметить" in ph for ph in data["hits"])


def test_obsidian_json(tmp_path):
    (tmp_path / "A.md").write_text("## Ок\n\n[текст](нет.md)\n",
                                   encoding="utf-8")
    data = _load(tmp_path, "oc.json",
                 lambda p: obsidian_check.run(str(tmp_path), exit_zero=True,
                                              json_out=p))
    assert data["tool"] == "obsidian-check"
    codes = {f["code"] for f in data["findings"]}
    assert "MDLINK_BROKEN" in codes
    assert all(f["severity"] in ("ERROR", "WARN", "INFO")
               for f in data["findings"])


def test_write_json_to_stdout(capsys):
    write_json("-", {"tool": "тест", "items": ["а", "б"]})
    data = json.loads(capsys.readouterr().out)
    assert data["tool"] == "тест"
    assert data["items"] == ["а", "б"]
