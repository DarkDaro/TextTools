"""
Тесты профиля «проверить всё» (full_check): четыре проверки одним
прогоном, сводка, агрегированный JSON, коды выхода.

Запуск:  python -m pytest test/test_full_check.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools import full_check


def test_clean_vault_returns_zero(tmp_path):
    (tmp_path / "ок.md").write_text("## Заголовок\n\nТекст.\n",
                                    encoding="utf-8")
    rc = full_check.run(str(tmp_path))
    assert rc == 0


def test_serious_findings_return_one(tmp_path):
    # ERROR валидатора: незакрытый код-блок
    (tmp_path / "плохо.md").write_text("## Ок\n\n```\nнезакрытый\n",
                                       encoding="utf-8")
    rc = full_check.run(str(tmp_path))
    assert rc == 1
    # --exit-zero гасит код
    assert full_check.run(str(tmp_path), exit_zero=True) == 0


def test_aggregated_json(tmp_path):
    (tmp_path / "плохо.md").write_text("## Ок\n\n```\nнезакрытый\n",
                                       encoding="utf-8")
    j = tmp_path / "rep" / "сводка.json"
    full_check.run(str(tmp_path), json_out=str(j))
    data = json.loads(j.read_text(encoding="utf-8"))
    assert data["tool"] == "check-all"
    assert data["serious"] is True
    assert set(data["checks"]) == {"obsidian-check", "cjk", "integrity",
                                   "merge-finder", "phrase-check",
                                   "antiresolve"}
    assert any(f["code"] == "FENCE_UNCLOSED"
               for f in data["checks"]["obsidian-check"]["findings"])


def test_check_all_cjk_sees_docx(tmp_path):
    # 05.11: cjk внутри «проверить всё» видит docx — раньше главы в docx
    # молча пропускались как бинарники, сводка отдавала ложное «чисто»
    from docx import Document
    doc = Document()
    doc.add_paragraph("Мусор от модели: 测试")
    doc.save(tmp_path / "глава.docx")
    (tmp_path / "ок.md").write_text("## Заголовок\n\nТекст.\n",
                                    encoding="utf-8")
    j = tmp_path / "rep" / "сводка.json"
    full_check.run(str(tmp_path), json_out=str(j))
    data = json.loads(j.read_text(encoding="utf-8"))
    cjk_results = data["checks"]["cjk"]["results"]
    assert any("глава.docx" in k for k in cjk_results)


def test_check_all_counts_stamps_and_resolve(tmp_path):
    # 05.11: штампы и АНТИРЕШИМОСТЬ — шаги 5/6 и 6/6, скан без записи;
    # стилистика не «серьёзное» — код остаётся 0
    (tmp_path / "ок.md").write_text(
        "## Заголовок\n\nСтоит отметить, что она с решимостью "
        "посмотрела на него и превозмогла боль.\n",
        encoding="utf-8")
    j = tmp_path / "rep" / "сводка.json"
    rc = full_check.run(str(tmp_path), json_out=str(j))
    data = json.loads(j.read_text(encoding="utf-8"))
    assert data["checks"]["phrase-check"].get("total", 0) >= 1
    ar = data["checks"]["antiresolve"]
    assert ar.get("hard", 0) >= 1
    assert data["serious"] is False
    assert rc == 0


def test_cli_help_and_wiring():
    # несуществующая папка — код 2, без трейсбека
    rc = full_check.main(["--input", "нет_такой_папки", "--limit", "1",
                          "--exit-zero"])
    assert rc == 2


def test_json_stdout_is_pure(tmp_path, capsys):
    # 05.11: «--json -» — stdout только JSON (сводка и вывод вложенных
    # проверок уходят в stderr); раньше всё мешалось в одном потоке
    (tmp_path / "плохо.md").write_text("## Ок\n\n```\nнезакрытый\n",
                                       encoding="utf-8")
    rc = full_check.run(str(tmp_path), json_out="-")
    assert rc == 1
    captured = capsys.readouterr()
    data = json.loads(captured.out)  # не-JSON в stdout заставит тест упасть
    assert data["tool"] == "check-all"
    assert data["serious"] is True
    assert "СВОДКА" in captured.err  # человеческая сводка не потеряна


def test_md_out_written(tmp_path):
    # 05.11 (BACKLOG №5): --out — человекочитаемая md-сводка шести
    # проверок в файл-журнал
    (tmp_path / "плохо.md").write_text(
        "## Ок\n\n```\nнезакрытый\n\nСтоит отметить, что всё плохо.\n",
        encoding="utf-8")
    out = tmp_path / "журнал" / "сводка.md"
    full_check.run(str(tmp_path), out=str(out))
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Проверить всё — сводка")
    assert "| Проверка | Итог |" in text
    assert "FENCE_UNCLOSED" in text  # ERROR валидатора попал в раздел
    assert "стоит отметить, что" in text  # штампы перечислены
    assert "Серьёзные замечания: есть" in text


def test_md_out_clean_vault(tmp_path):
    (tmp_path / "ок.md").write_text("## Заголовок\n\nТекст.\n",
                                    encoding="utf-8")
    out = tmp_path / "сводка.md"
    full_check.run(str(tmp_path), out=str(out))
    text = out.read_text(encoding="utf-8")
    assert "Серьёзные замечания: нет." in text
    assert "не найдено" in text  # пустые секции честные, не пропущены


def test_md_out_stdout(capsys, tmp_path):
    # «--out -» печатает md в stdout
    (tmp_path / "ок.md").write_text("## Заголовок\n\nТекст.\n",
                                    encoding="utf-8")
    full_check.run(str(tmp_path), out="-")
    captured = capsys.readouterr()
    assert "# Проверить всё — сводка" in captured.out
