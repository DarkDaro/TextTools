# -*- coding: utf-8 -*-
"""Тесты движка АНТИРЕШИМОСТЬ (tools.antiresolve): поиск, лог, зачистка."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import antiresolve  # noqa: E402

# Пример «до» из памятки (п.5): все три вида находок — hard
BEFORE = ("Она с решимостью посмотрела на врага. В её глазах горел огонь. "
          "Она превозмогла страх и шагнула вперёд.")


def test_scan_dry_run(tmp_path, monkeypatch):
    """Сухой прогон: находки в сводке и логе, файл не правится."""
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "a.md"
    f.write_text(BEFORE, encoding="utf-8")
    rc, log, summary = antiresolve.run(str(f))
    assert rc == 1
    assert summary["hard"] == 3  # «с решимостью», «глазах горел», «превозмогла»
    assert "решимость/hard" in summary["по_категориям"]
    assert f.read_text(encoding="utf-8") == BEFORE
    log_f = tmp_path / "reports" / "antiresolve.log"
    assert log_f.exists()
    body = log_f.read_text(encoding="utf-8")
    assert "решимость" in body
    assert "→" in body  # подсказка редактору рядом с находкой


def test_phrase_rule_priority(tmp_path, monkeypatch):
    """«с решимостью» — одно вхождение (фраза побеждает корневое правило)."""
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "p.md"
    f.write_text("Он с решимостью кивнул.", encoding="utf-8")
    rc, log, summary = antiresolve.run(str(f))
    assert rc == 1
    assert summary["hard"] == 1


def test_clean_md(tmp_path, monkeypatch):
    """Зачистка: hard вырезаны (оборот «с решимостью» целиком), .bak есть."""
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "c.md"
    f.write_text(BEFORE, encoding="utf-8")
    rc, log, summary = antiresolve.run(str(f), clean=True)
    after = f.read_text(encoding="utf-8")
    for word in ("решимост", "превозмог", "глазах горел"):
        assert word not in after
    assert "с решительностью" not in after
    # вырезание не склеивает слова и не оставляет двойных пробелов
    assert "Она посмотрела на врага." in after
    assert "  " not in after
    assert f.with_suffix(".md.bak").exists()
    assert summary["осталось"]["hard"] == 0
    assert summary["осталось"]["soft"] == 0
    assert rc == 0


def test_soft_never_cut(tmp_path, monkeypatch):
    """soft-правила не вырезаются даже при --clean («надежда» — на усмотрение автора)."""
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "s.md"
    f.write_text("Впереди была надежда. Всё как всегда.", encoding="utf-8")
    rc, log, summary = antiresolve.run(str(f), clean=True)
    assert "надежд" in f.read_text(encoding="utf-8")
    assert summary["осталось"]["hard"] == 0
    assert summary["осталось"]["soft"] == 1
    assert rc == 0  # soft в код возврата не входит


def test_clean_docx(tmp_path, monkeypatch):
    """Зачистка docx: фраза вырезана, остальной текст цел."""
    pytest.importorskip("docx")
    from docx import Document
    from core import docx_io
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "d.docx"
    doc = Document()
    doc.add_paragraph("Он с решимостью шагнул вперёд. Всё просто.")
    doc.add_paragraph("Вторая строка остаётся нетронутой.")
    doc.save(str(f))
    rc, log, summary = antiresolve.run(str(f), clean=True)
    text = docx_io.read_text(f)
    assert "решимост" not in text.lower()
    assert "Он шагнул вперёд. Всё просто." in text
    assert "Вторая строка остаётся нетронутой." in text
    assert summary["осталось"]["hard"] == 0
    assert rc == 0
    assert summary["зачистка"]["файлов"] == 1


def test_json_summary(tmp_path, monkeypatch):
    """--json в файл: структура сводки парсится, категории на месте."""
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "e.md"
    f.write_text("Он превозмог боль и встал.", encoding="utf-8")
    jf = tmp_path / "sum.json"
    rc = antiresolve.main(["--input", str(f), "--json", str(jf)])
    data = json.loads(jf.read_text(encoding="utf-8"))
    assert data["hard"] == 1
    assert "превозмогание/hard" in data["по_категориям"]
    assert data["зачистка"] is None
    assert rc == 1


def test_bad_input_rc2(tmp_path):
    """Несуществующий --input — код 2, без трейсбека."""
    rc = antiresolve.main(["--input", str(tmp_path / "нет")])
    assert rc == 2


def test_log_appends(tmp_path, monkeypatch):
    """Лог-текстовик дописывается: два прогона — два блока ===."""
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "l.md"
    f.write_text("Мы не отступим.", encoding="utf-8")
    antiresolve.run(str(f))
    antiresolve.run(str(f))
    body = (tmp_path / "reports" / "antiresolve.log").read_text(encoding="utf-8")
    assert body.count("=== АНТИРЕШИМОСТЬ") == 2
    assert "лозунг" in body


def test_cli_subcommand_and_alias(tmp_path):
    """textools.py antiresolve и алиас pathos: подкоманда работает,
    «--out -» и «--json -» дают чистый stdout."""
    import subprocess
    root = Path(__file__).resolve().parent.parent
    f = tmp_path / "cli.md"
    f.write_text("Она превозмогла боль.", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, "textools.py", "antiresolve", "--input", str(f),
         "--log", str(tmp_path / "cli.log"), "--out", "-"],
        cwd=root, capture_output=True, text=True)
    assert r.returncode == 1
    assert "превозмог" in r.stdout
    r2 = subprocess.run(
        [sys.executable, "textools.py", "pathos", "--input", str(f),
         "--log", str(tmp_path / "cli.log"), "--json", "-"],
        cwd=root, capture_output=True, text=True)
    assert r2.returncode == 1
    data = json.loads(r2.stdout)  # stdout — чистый JSON, без служебных строк
    assert data["hard"] == 1
    assert "превозмогание/hard" in data["по_категориям"]


def test_run_collect_adds_findings(tmp_path):
    """05.11: collect=True добавляет «находки» в сводку (нужно
    check-all --plan); без collect сводка компактна, как раньше."""
    from tools import antiresolve
    f = tmp_path / "глава.md"
    f.write_text("Она превозмогла боль.", encoding="utf-8")
    _rc, _log, summary = antiresolve.run(
        str(f), quiet=True, log_path=str(tmp_path / "a.log"),
        collect=True)
    items = summary["находки"]
    assert len(items) == 1
    assert items[0]["жёсткость"] == "hard"
    assert items[0]["файл"] == str(f)
    assert "фрагмент" in items[0] and "категория" in items[0]
    # без collect — ключа нет (JSON сводок не раздувается)
    _rc, _log, summary2 = antiresolve.run(
        str(f), quiet=True, log_path=str(tmp_path / "b.log"))
    assert "находки" not in summary2
