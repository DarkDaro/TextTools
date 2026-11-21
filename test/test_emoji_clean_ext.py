# 21.11: новые режимы emoji-cleaner — --invisible, --ws, --ai-scan.
# Скрипт разбирает sys.argv при импорте, поэтому гоняется подпроцессом —
# так же, как его запускают обёртка и пользователь. Обычная чистка
# (эмодзи/смайлы) проверяется на регресс: старое поведение не изменилось.
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
CLEAN = HERE / "external" / "emoji-cleaner" / "clean.py"

ZWSP = "\u200b"
TAG = "\U000e0000"   # тег-символ — типовой носитель водяного знака ИИ
SHY = "\u00ad"
THIN = "\u2009"      # узкий пробел


def run_clean(args):
    return subprocess.run([sys.executable, str(CLEAN), *args],
                          capture_output=True, text=True, timeout=120)


def test_old_mode_unchanged(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("Привет 😀 мир :)\n", encoding="utf-8")
    r = run_clean([str(f), "--dry-run"])
    assert r.returncode == 0
    assert "эмодзи 1, смайлов 1" in r.stdout
    # старый формат итоговой строки — без новых хвостов
    assert "невидимых" not in r.stdout and "табов" not in r.stdout
    assert f.read_text(encoding="utf-8") == "Привет 😀 мир :)\n"


def test_invisible_dry_run_counts(tmp_path):
    f = tmp_path / "b.md"
    f.write_text(f"тихий{SHY}шаг и знак{TAG}конец\n", encoding="utf-8")
    r = run_clean([str(f), "--invisible", "--dry-run"])
    assert r.returncode == 0
    assert "невидимых 2 (shy 1, tag 1)" in r.stdout
    assert f.read_text(encoding="utf-8") == f"тихий{SHY}шаг и знак{TAG}конец\n"


def test_invisible_real_run_removes(tmp_path):
    f = tmp_path / "c.md"
    f.write_text(f"знак{TAG}внутри\n", encoding="utf-8")
    r = run_clean([str(f), "--invisible"])
    assert r.returncode == 0
    assert f.read_text(encoding="utf-8") == "знаквнутри\n"


def test_invisible_inside_fence(tmp_path):
    # в код-блоке ZWSP и так убирается эмодзи-проходом как служебный
    # код; тег-символ эмодзи-проход не трогает — его ловит --invisible
    f = tmp_path / "d.md"
    f.write_text(f"```py\nx = 1{TAG}  # комментарий\n```\n", encoding="utf-8")
    r = run_clean([str(f), "--invisible", "--dry-run"])
    assert r.returncode == 0
    assert "невидимых 1 (tag 1)" in r.stdout


def test_ws_tabs_and_spaces(tmp_path):
    f = tmp_path / "e.md"
    f.write_text("слово\tтаб ещё\tдва\nотступ\tне важен\tтут\n",
                 encoding="utf-8")
    r = run_clean([str(f), "--ws", "--dry-run"])
    assert r.returncode == 0
    assert "табов/пробелов 4" in r.stdout
    f2 = tmp_path / "f.md"
    f2.write_text(f"узкий{THIN}пробел\n", encoding="utf-8")
    r2 = run_clean([str(f2), "--ws"])
    assert r2.returncode == 0
    assert f2.read_text(encoding="utf-8") == "узкий пробел\n"


def test_ws_keeps_code_fence(tmp_path):
    f = tmp_path / "g.md"
    f.write_text("```py\na\tb\n```\n", encoding="utf-8")
    r = run_clean([str(f), "--ws", "--dry-run"])
    assert "изменено 0" in r.stdout


def test_ai_scan_clean_and_dirty(tmp_path):
    ok = tmp_path / "ok.md"
    ok.write_text("совершенно чистой текст без следов\n", encoding="utf-8")
    r = run_clean([str(ok), "--ai-scan"])
    assert r.returncode == 0
    assert "чисто" in r.stdout

    bad = tmp_path / "bad.md"
    bad.write_text(f"подмена аdон и знак{TAG}\n", encoding="utf-8")
    r2 = run_clean([str(bad), "--ai-scan"])
    assert r2.returncode == 1
    assert "ЕСТЬ СЛЕДЫ" in r2.stdout
    assert "подменённых слов 1" in r2.stdout
    assert "tag 1" in r2.stdout


def test_ai_scan_docx_hidden_white(tmp_path):
    from docx import Document
    from docx.oxml.ns import qn

    d = Document()
    d.add_paragraph(f"обычный текст с{SHY}мягким")
    r = d.add_paragraph().add_run("скрытая метка")
    r._r.get_or_add_rPr().append(r._r.makeelement(qn("w:vanish"), {}))
    r2 = d.add_paragraph().add_run("белая строка")
    r2._r.get_or_add_rPr().append(
        r2._r.makeelement(qn("w:color"), {qn("w:val"): "FFFFFF"}))
    p = tmp_path / "h.docx"
    d.save(p)

    out = tmp_path / "rep.json"
    r = run_clean([str(p), "--ai-scan", "--json", str(out)])
    assert r.returncode == 1
    assert "скрытых текстов 1" in r.stdout
    assert "белых текстов 1" in r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ok"] is False
    files = list(doc["files"].values())
    assert files[0]["hidden"][0][1] == "скрытая метка"
    assert files[0]["white"][0][1] == "белая строка"


def test_restore_incompatible_with_new_flags(tmp_path):
    r = run_clean([str(tmp_path), "--restore", "--ai-scan"])
    assert r.returncode == 1
    assert "Несовместимо" in r.stdout
