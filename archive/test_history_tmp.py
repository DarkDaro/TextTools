# Временный функциональный тест журнала операций (02.10)
import sys, time, os
sys.path.insert(0, "archive")
sys.path.insert(0, os.getcwd())
import gen_corpus
gen_corpus.main()

import customtkinter
import gui_ctk
from gui_ctk import App, HISTORY_FILE

app = App()
app.update()

# кнопка журнала на вкладке настроек
btns = []
def walk(w):
    for ch in w.winfo_children():
        if isinstance(ch, customtkinter.CTkButton):
            btns.append(str(ch.cget("text")))
        walk(ch)
walk(app)
print("HIST_BUTTON:", "Открыть журнал" in btns)

print("HAS_RUNNER:", hasattr(app, "runner"))
r = getattr(app, "runner", None)
if r is None:
    # возможно Runner называется иначе
    print("ATTRS:", [a for a in dir(app) if "run" in a.lower()])
    sys.exit(1)

os.makedirs("archive/_tmp_hist", exist_ok=True)
with open("archive/_tmp_hist/a.md", "w", encoding="utf-8") as f:
    f.write("Привет мир. Тест журнала операций.\n")

cmd = [sys.executable, "textools.py", "stats", "--input", "archive/_tmp_hist"]
r.run(cmd, cwd=os.getcwd())
for _ in range(300):
    app.update()
    if not r.running:
        break
    time.sleep(0.03)

time.sleep(0.2)
print("HIST_EXISTS:", HISTORY_FILE.exists())
if HISTORY_FILE.exists():
    lines = HISTORY_FILE.read_text(encoding="utf-8").strip().splitlines()
    print("HIST_LINES:", len(lines))
    for ln in lines[-2:]:
        print("LINE:", ln)
    has_start = any("| START |" in ln and "textools.py stats" in ln for ln in lines)
    has_done = any("| DONE" in ln and "код 0" in ln for ln in lines)
    print("START_OK:", has_start, "DONE_OK:", has_done)

app.destroy()
print("TMP_TEST_DONE")
