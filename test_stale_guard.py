# Тест «старая копия не запускается»: gui_ctk._stale_redirect.
# 08.11: маркер canonical.txt пишет патник (ярлыки/папка). Защита
# обязана: молчать без маркера/на основной копии/при протухшем маркере
# и эстафовать запуск при копии старше канонической.
import importlib.util
import os
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = Path(__file__).parent

def _load_gui():
    loader = SourceFileLoader("gui_ctk", str(HERE / "gui_ctk.pyw"))
    spec = importlib.util.spec_from_loader("gui_ctk", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gui_ctk"] = mod
    loader.exec_module(mod)
    return mod

gui = _load_gui()

# Заглушки: диалог и запуск чужого процесса не должны происходить по-настоящему.
import tkinter.messagebox as _mb
calls = {"info": 0, "popen": []}
_mb.showinfo = lambda *a, **k: calls.__setitem__("info", calls["info"] + 1)
gui.subprocess.Popen = lambda *a, **k: calls["popen"].append(a[0] if a else k)

def _write_marker(appdata, text, encoding="utf-8"):
    d = Path(appdata) / "TextTools"
    d.mkdir(parents=True, exist_ok=True)
    (d / "canonical.txt").write_text(text, encoding=encoding)

def _fake_copy(tmp, version):
    c = Path(tmp) / "CanonicalTool"
    c.mkdir(parents=True, exist_ok=True)
    (c / "textools.py").write_text(f'__version__ = "{version}"\n', encoding="utf-8")
    (c / "gui_ctk.pyw").write_text("", encoding="utf-8")
    return c

def _runs_guard():
    """Возврат из _stale_redirect (запуск разрешён)?"""
    try:
        gui._stale_redirect()
        return True
    except SystemExit:
        return False

ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond)
    fail += (not cond)
    print(("  ok  " if cond else "  FAIL ") + name)

tmp = tempfile.mkdtemp()

# [1] APPDATA пуст — защита молчит
old_appdata = os.environ.get("APPDATA")
os.environ["APPDATA"] = ""
check("пустой APPDATA — молчит", _runs_guard())

# [2] маркера нет — молчит
os.environ["APPDATA"] = str(Path(tmp) / "no_marker")
check("нет маркера — молчит", _runs_guard())

# [3] маркер есть, папки нет (протух) — молчит
os.environ["APPDATA"] = str(Path(tmp) / "rotten")
_write_marker(os.environ["APPDATA"], str(Path(tmp) / "deleted_copy"))
check("протухший маркер — молчит", _runs_guard())

# [4] каноническая = эта же папка — молчит
os.environ["APPDATA"] = str(Path(tmp) / "self")
_write_marker(os.environ["APPDATA"], str(HERE))
check("каноническая — это мы — молчит", _runs_guard())

# [5] каноническая старее — молчит, работаем
os.environ["APPDATA"] = str(Path(tmp) / "older")
_write_marker(os.environ["APPDATA"], str(_fake_copy(tmp, "0.0.1")))
check("каноническая старее — молчит", _runs_guard())

# [6] каноническая новее — эстафета: диалог + запуск + выход
os.environ["APPDATA"] = str(Path(tmp) / "newer")
c6 = _fake_copy(tmp, "9.9.9")
_write_marker(os.environ["APPDATA"], str(c6))
exited = False
try:
    gui._stale_redirect()
except SystemExit:
    exited = True
check("каноническая новее — программа выходит", exited)
check("каноническая новее — показан диалог", calls["info"] == 1)
check("каноническая новее — запущена свежая копия",
      bool(calls["popen"]) and str(c6) in str(calls["popen"][0]))

# [7] версия канонической не парсится — молчит (не ломать запуск)
calls["info"] = 0
os.environ["APPDATA"] = str(Path(tmp) / "garbage")
c7 = _fake_copy(tmp, "9.9.9")
(c7 / "textools.py").write_text("это не версия вообще", encoding="utf-8")
_write_marker(os.environ["APPDATA"], str(c7))
check("мусор вместо версии — молчит", _runs_guard() and calls["info"] == 0)

# [8] маркер с BOM и кавычками (закладка на формат записи патника) — эстафета
calls["popen"].clear()
os.environ["APPDATA"] = str(Path(tmp) / "bom")
c8 = _fake_copy(tmp, "9.9.8")
_write_marker(os.environ["APPDATA"], f'"{c8}"', encoding="utf-8-sig")
exited = False
try:
    gui._stale_redirect()
except SystemExit:
    exited = True
check("BOM + кавычки в маркере — эстафета работает",
      exited and bool(calls["popen"]) and str(c8) in str(calls["popen"][0]))

if old_appdata is None:
    os.environ.pop("APPDATA", None)
else:
    os.environ["APPDATA"] = old_appdata

print(f"\nИтого: ок {ok}, провал {fail}")
sys.exit(1 if fail else 0)
