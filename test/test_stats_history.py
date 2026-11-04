"""
Тесты stats --history: динамика объёма из дневника reports/stats_log.csv.

05.11 (BACKLOG №3): дневник уже копился (stats --csv), но смотреть на
него можно было только в Excel. --history печатает слова по датам,
дельты и темп в день.

Запуск:  python -m pytest test/test_stats_history.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import text_stats


def _make_diary(tmp_path, rows):
    p = tmp_path / "stats_log.csv"
    head = "дата;файл;слов;предложений;средняя длина;диалогов %\n"
    p.write_text(head + "".join(r + "\n" for r in rows), encoding="utf-8-sig")
    return p


def test_history_deltas_and_tempo(tmp_path, capsys):
    p = _make_diary(tmp_path, [
        "2026-11-01 10:00;глава1.md;10000;500;20.0;30",
        "2026-11-03 12:00;глава1.md;10700;540;19.8;31",
        "2026-11-03 18:00;глава1.md;10800;545;19.8;31",
    ])
    rc = text_stats.history(csv_path=p)
    assert rc == 0
    out = capsys.readouterr().out
    # два запуска за 03.11 — берётся последний, удвоения нет
    assert "10800" in out and "10700" not in out
    assert "+800" in out          # дельта с 01.11
    assert "темп ~400/день" in out  # +800 за 2 дня
    assert "за 2 дн." in out


def test_history_missing_diary(tmp_path, capsys):
    rc = text_stats.history(csv_path=tmp_path / "нет.csv")
    assert rc == 1
    assert "Дневник пуст" in capsys.readouterr().out


def test_history_single_date(tmp_path, capsys):
    p = _make_diary(tmp_path, [
        "2026-11-05 09:00;глава1.md;5000;250;20.0;25",
    ])
    rc = text_stats.history(csv_path=p)
    assert rc == 0
    out = capsys.readouterr().out
    assert "минимум две разные даты" in out


def test_history_md_report(tmp_path):
    p = _make_diary(tmp_path, [
        "2026-11-01 10:00;глава1.md;10000;500;20.0;30",
        "2026-11-04 10:00;глава1.md;13000;650;20.0;30",
    ])
    out = tmp_path / "история.md"
    rc = text_stats.history(csv_path=p, out=str(out))
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "| Дата | записей | слов | дельта |" in text
    assert "| 2026-11-04 | 1 | 13000 | +3000 |" in text
    assert "Темп: ~1000 слов/день" in text


def test_history_skips_broken_rows(tmp_path, capsys):
    p = _make_diary(tmp_path, [
        "2026-11-01 10:00;глава1.md;10000;500;20.0;30",
        "мусорная;строка",
        "2026-11-02 10:00;глава1.md;не-число;1;1;1",
        "2026-11-02 10:00;глава2.md;10200;510;20.0;30",
    ])
    rc = text_stats.history(csv_path=p)
    assert rc == 0
    out = capsys.readouterr().out
    assert "+200" in out  # битая строка пропущена, числовая учтена


def test_cli_wiring(monkeypatch, tmp_path, capsys):
    # textools.py stats --history: --input не нужен, дневник из reports/
    p = _make_diary(tmp_path, [
        "2026-11-01 10:00;глава1.md;10000;500;20.0;30",
        "2026-11-02 10:00;глава1.md;10500;520;20.0;30",
    ])
    monkeypatch.setattr(text_stats, "HISTORY_FILE", p)
    assert text_stats.main(["--history"]) == 0
    assert "+500" in capsys.readouterr().out


def test_cli_requires_input_without_history():
    r = subprocess.run(
        [sys.executable, "textools.py", "stats"],
        cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 2
    assert "--input" in r.stderr


def test_stats_help_mentions_history():
    r = subprocess.run(
        [sys.executable, "textools.py", "stats", "--help"],
        cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0
    assert "--history" in r.stdout
