# -*- coding: utf-8 -*-
"""Проверка автопоиска внешних скриптов и пресетов.

Запуск: py -3.14 test_script_presets.py
"""
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import gui_config
import wrappers

MARKERS = {
    "emoji_cleaner": ("эмодзи", "--restore"),
    "clean_text": ("clean_text_files", "китайских"),
    "md_replace": ("Массовая автозамена", "--dry-run"),
    "char_search": ("Поиск персонажей", "--vault"),
    "refile": ("массовое редактирование", "--exts"),
}


def touch(path, key=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "# test\n"
    if key:
        text += "\n".join(MARKERS[key]) + "\n"
    path.write_text(text, encoding="utf-8")


def test_find_scripts_layout():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        touch(root / "emoji-cleaner" / "clean.py", "emoji_cleaner")
        touch(root / "scripts" / "Archive" / "herodata" /
              "clean_text_files.py", "clean_text")
        touch(root / "md-replace" / "md_replace.py", "md_replace")
        touch(root / "md-replace" / "char_search.py", "char_search")
        touch(root / "refile.py", "refile")
        found = wrappers.find_scripts(root=root)
        assert set(found) == set(wrappers.SCRIPT_CANDIDATES), found
        for key, value in found.items():
            assert Path(value).is_file(), (key, value)
    print("ok: автопоиск находит все пять скриптов")


def test_find_scripts_rejects_lookalike():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "refile.py").write_text("# чужой скрипт\n", encoding="utf-8")
        found = wrappers.find_scripts(root=root)
        assert "refile" not in found, found
    print("ok: одноимённый чужой файл не проходит автопоиск")


def test_default_scripts_refresh():
    old_env = os.environ.get("TEXTOOLS_SCRIPTS_DIR")
    try:
        with tempfile.TemporaryDirectory() as td1, \
                tempfile.TemporaryDirectory() as td2:
            touch(Path(td1) / "refile.py", "refile")
            os.environ["TEXTOOLS_SCRIPTS_DIR"] = td1
            first = wrappers.default_scripts()
            assert Path(first.get("refile", "")).is_file(), first

            touch(Path(td2) / "md_replace.py", "md_replace")
            os.environ["TEXTOOLS_SCRIPTS_DIR"] = td2
            second = wrappers.default_scripts()
            assert Path(second.get("md_replace", "")).is_file(), second
    finally:
        if old_env is None:
            os.environ.pop("TEXTOOLS_SCRIPTS_DIR", None)
        else:
            os.environ["TEXTOOLS_SCRIPTS_DIR"] = old_env
    print("ok: смена TEXTOOLS_SCRIPTS_DIR сбрасывает кэш автопоиска")


def test_script_path_precedence():
    old = gui_config._config
    try:
        with tempfile.TemporaryDirectory() as td:
            custom = Path(td) / "custom_md_replace.py"
            touch(custom)
            gui_config._config = {
                "script_preset": "manual",
                "script_md_replace": str(custom),
            }
            assert wrappers.script_path("md_replace") == str(custom)
            assert wrappers.script_source("md_replace") == "custom"

            gui_config._config["script_preset"] = "off"
            assert wrappers.script_path("md_replace") == ""
    finally:
        gui_config._config = old
    print("ok: ручной путь главнее автопоиска, пресет off отключает")


def main():
    test_find_scripts_layout()
    test_find_scripts_rejects_lookalike()
    test_default_scripts_refresh()
    test_script_path_precedence()
    print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")


if __name__ == "__main__":
    main()
