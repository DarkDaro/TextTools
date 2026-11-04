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
                                   "merge-finder"}
    assert any(f["code"] == "FENCE_UNCLOSED"
               for f in data["checks"]["obsidian-check"]["findings"])


def test_cli_help_and_wiring():
    # несуществующая папка — код 2, без трейсбека
    rc = full_check.main(["--input", "нет_такой_папки", "--limit", "1",
                          "--exit-zero"])
    assert rc == 2
