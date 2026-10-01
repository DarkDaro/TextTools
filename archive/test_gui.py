# -*- coding: utf-8 -*-
"""Полный GUI-тест textools: каждая кнопка и опция каждой вкладки.

Запускается без ручного кликанья: создаёт App, «прожимает» update(),
нажимает кнопки через invoke(), проверяет лог. Все запуски — на
archive/corpus (пересоздаётся gen_corpus.py), реальные замены — dry-run,
кроме помеченных (данные корпуса регенерируемые).

Запуск: python test_gui.py
"""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

# свежий корпус для GUI-прогонов
subprocess.run([sys.executable, str(HERE / "gen_corpus.py")], check=True)

import gui_ctk  # noqa: E402
from gui_config import CFG  # noqa: E402
from widgets_ctk import CheckField, EntryField, PathField, BigButton, HelpBox  # noqa: E402

CORPUS = HERE / "corpus"
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append((name, detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  | {detail}" if detail and not cond else ""))


app = gui_ctk.App()


def pump(ms=1200):
    end = time.time() + ms / 1000
    while time.time() < end:
        app.update()
        time.sleep(0.02)


def log_text():
    return app.log.get("1.0", "end")


def run_and_wait(timeout=30000):
    end = time.time() + timeout / 1000
    while time.time() < end:
        app.update()
        if "[завершено" in log_text() or "ошибка запуска" in log_text():
            pump(300)
            return True
        time.sleep(0.05)
    return False


def click(container, label):
    def walk(w):
        yield w
        for c in w.winfo_children():
            yield from walk_all(c)
    for w in walk(container):
        try:
            if w.cget("text") == label:
                w.invoke()
                return True
        except Exception:
            pass
    return False


def walk_all(w):
    yield w
    for c in w.winfo_children():
        yield from walk_all(c)


pump(1200)

# --- структура ---
tabs = list(app.nb._tab_dict.keys())
for t in ("Имена персонажей", "Хранилище", "Чистка", "Замены", "Настройки"):
    check(f"вкладка: {t}", t in tabs)

from tabs_names import NamesTab
from tabs_vault import VaultTab
from tabs_clean import CleanTab
from tabs_replace import ReplaceTab
from tabs_settings import SettingsTab


def find_tab(cls):
    for frame in app.nb._tab_dict.values():
        for w in walk_all(frame):
            if isinstance(w, cls):
                return w
    return None


names, vault = find_tab(NamesTab), find_tab(VaultTab)
clean, repl, sett = find_tab(CleanTab), find_tab(ReplaceTab), find_tab(SettingsTab)
for n, t in (("Names", names), ("Vault", vault), ("Clean", clean),
             ("Replace", repl), ("Settings", sett)):
    check(f"вкладка создана: {n}", t is not None)

# регресс: ни одного неупакованного виджета
unpacked = []
for frame in app.nb._tab_dict.values():
    for w in walk_all(frame):
        if isinstance(w, (CheckField, PathField, EntryField, BigButton)):
            try:
                w.pack_info()
            except Exception:
                unpacked.append(w)
check("нет невидимых (неупакованных) виджетов", not unpacked)

# регресс 01.10: у VaultTab и NamesTab должен быть свой _log (без него
# валидации и кнопки штампов падали с AttributeError) — monkeypatch не нужен
check("VaultTab._log существует", hasattr(type(vault), "_log"))
check("NamesTab._log существует", hasattr(type(names), "_log"))

# ================= Вкладка «Имена персонажей» =================
app.log.delete("1.0", "end")
names.f_input.var.set(str(CORPUS / "names"))
names.min_count.var.set("1")
check("Имена: Найти кандидатов", click(names, "Найти кандидатов") and run_and_wait()
      and "Кандидаты-слова" in log_text())
app.log.delete("1.0", "end")
names.min_count.var.set("10")
check("Имена: min-count=10 фильтрует", click(names, "Найти кандидатов") and run_and_wait()
      and "Кандидаты-слова (частота >= 10): 0" in log_text())
names.min_count.var.set("1")
app.log.delete("1.0", "end")
names.f_cons_input.var.set(str(CORPUS / "names"))
names.f_cons_reg.var.set(str(CORPUS / "names" / "registry.yaml"))
check("Имена: Проверить имена", click(names, "Проверить имена") and run_and_wait()
      and "Проблемных персонажей" in log_text())
app.log.delete("1.0", "end")
names.f_cons_input.var.set("")
check("Имена: валидация пустой папки", click(names, "Проверить имена")
      and "Укажите папку" in log_text() and not app.runner.running)

# ================= Вкладка «Хранилище» =================
app.log.delete("1.0", "end")
vault.f_vault.var.set(str(CORPUS / "vault"))
for btn, marker in (("Orphans (одиночки)", "Orphan"),
                    ("Битые ссылки", "Битых ссылок: 1"),
                    ("Дубликаты (merge)", "Дубликатов по содержимому: 1")):
    app.log.delete("1.0", "end")
    check(f"Хранилище: {btn}", click(vault, btn) and run_and_wait() and marker in log_text())

# «Сохранять отчёт в reports/» (теперь видимый чекбокс)
vault.c_report.set(True)
app.log.delete("1.0", "end")
check("Хранилище: Orphans + отчёт в reports/", click(vault, "Orphans (одиночки)")
      and run_and_wait())
reports = ROOT / "reports"
check("Хранилище: отчёт-файл создан", (reports / "orphan_finder.md").exists())
vault.c_report.set(False)

# phrase_check: найти штампы
app.log.delete("1.0", "end")
vault.f_pc.var.set(str(CORPUS / "stamps"))
vault.f_pc_phrase.var.set("с каждым днем")
check("Хранилище: Найти штампы (своя фраза)", click(vault, "Найти штампы")
      and run_and_wait() and "Файлов проверено" in log_text())
app.log.delete("1.0", "end")
vault.f_pc.var.set("")
check("Хранилище: валидация пустого пути штампов", click(vault, "Найти штампы")
      and "Укажите папку" in log_text())

# почистить штампы (dry по чекбоксу)
vault.f_pc.var.set(str(CORPUS / "stamps"))
vault.c_pc_dry.set(True)
app.log.delete("1.0", "end")
check("Хранилище: Почистить штампы (dry)", click(vault, "Почистить штампы")
      and run_and_wait() and "DRY-RUN" in log_text())
vault.c_pc_dry.set(False)
app.log.delete("1.0", "end")
check("Хранилище: Почистить штампы (реально)", click(vault, "Почистить штампы")
      and run_and_wait() and "Изменено файлов" in log_text())

# ================= Вкладка «Чистка» =================
app.log.delete("1.0", "end")
clean.f_ws.var.set(str(CORPUS / "ws"))
clean.c_ws_fix.var.set(False)
check("Чистка: пробелы (dry)", click(clean, "Запустить чистку пробелов")
      and run_and_wait() and "Итого" in log_text() and "dry-run" in log_text().lower())
clean.c_ws_fix.var.set(True)
app.log.delete("1.0", "end")
check("Чистка: пробелы (применить)", click(clean, "Запустить чистку пробелов")
      and run_and_wait() and "[FIX]" in log_text())
clean.c_ws_fix.var.set(False)

app.log.delete("1.0", "end")
clean.f_emoji.var.set(str(CORPUS / "emoji"))
clean.c_dry.var.set(True)
check("Чистка: эмодзи (dry-run)", click(clean, "Запустить чистку эмодзи")
      and run_and_wait())
app.log.delete("1.0", "end")
clean.c_dry.var.set(False)
clean.c_bak.var.set(True)
check("Чистка: эмодзи (реально + .bak)", click(clean, "Запустить чистку эмодзи")
      and run_and_wait())
clean.c_bak.var.set(False)
clean.c_res.var.set(True)
app.log.delete("1.0", "end")
check("Чистка: эмодзи (восстановить из .bak)", click(clean, "Запустить чистку эмодзи")
      and run_and_wait())
clean.c_res.var.set(False)

app.log.delete("1.0", "end")
clean.f_text.var.set(str(CORPUS / "cjk"))
check("Чистка: мусор/CJK (отчёт)", click(clean, "Запустить чистку мусора")
      and run_and_wait())

# ================= Вкладка «Замены» =================
app.log.delete("1.0", "end")
repl.f_vault.var.set(str(CORPUS / "names"))
repl.f_old.var.set("Эрика")
repl.f_new.var.set("ГЕРДА")
repl.c_regex.var.set(False)
repl.c_apply.var.set(False)
check("Замены: md_replace (dry)", click(repl, "Заменить") and run_and_wait()
      and ("dry" in log_text().lower() or "DRY" in log_text()))
repl.c_apply.var.set(True)
app.log.delete("1.0", "end")
check("Замены: md_replace (применить)", click(repl, "Заменить") and run_and_wait())
repl.c_apply.var.set(False)
repl.c_regex.var.set(True)
app.log.delete("1.0", "end")
repl.f_old.var.set(r"Эрик\w+")
check("Замены: md_replace (regex)", click(repl, "Заменить") and run_and_wait())
repl.c_regex.var.set(False)

for btn in ("Найти проблемные символы", "Починить UTF-8", "Вырезать мусор"):
    app.log.delete("1.0", "end")
    repl.f_vault2.var.set(str(CORPUS / "enc"))
    repl.c_spec.var.set(False)
    ok = click(repl, btn) and run_and_wait()
    check(f"Замены: {btn} (dry)", ok)

app.log.delete("1.0", "end")
repl.f_cs_vault.var.set(str(CORPUS / "names"))
repl.c_fix.var.set(False)
check("Замены: Проверить (char_search)", click(repl, "Проверить") and run_and_wait())
app.log.delete("1.0", "end")
repl.f_csw_bad.var.set("Кайзо")
repl.f_csw_good.var.set("Кайдзо")
repl.c_fw_dry.var.set(True)
check("Замены: Заменить слово (dry)", click(repl, "Заменить слово") and run_and_wait())

app.log.delete("1.0", "end")
repl.f_rf.var.set(str(CORPUS / "refile"))
repl.f_pat.var.set(r"\d{2}\.\d{2}\.\d{4}")
repl.f_repl.var.set("ДАТА")
repl.f_exts.var.set("md txt")
repl.c_rf.var.set(False)
check("Замены: refile (dry, exts=md txt)", click(repl, "Запустить") and run_and_wait()
      and "dry" in log_text().lower())
repl.c_rf.var.set(True)
app.log.delete("1.0", "end")
check("Замены: refile (применить)", click(repl, "Запустить") and run_and_wait()
      and "ДАТА" in log_text())
repl.c_rf.var.set(False)

# ================= Вкладка «Настройки» =================
app.log.delete("1.0", "end")
check("Настройки: Сохранить сейчас", click(sett, "Сохранить сейчас")
      and "Настройки сохранены" in log_text())
# default_vault fallback в пустые *_input
CFG.set("default_vault", str(CORPUS))
cfg_probe = CFG.get("zz_probe_input")
check("Настройки: default_vault подставляется в пустые *_input", cfg_probe == str(CORPUS))
# «Открыть конфиг» не жмём — откроет Блокнот; «Сбросить всё» не жмём — удалит конфиг (правило: ничего не удалять)

# ================= Новое 01.10: матрица, падежи, UTF-8, витрина =================
app.log.delete("1.0", "end")
names.f_mat_input.var.set(str(CORPUS / "names"))
names.f_mat_reg.var.set(str(CORPUS / "names" / "registry.yaml"))
check("Имена: Построить матрицу", click(names, "Построить матрицу") and run_and_wait()
      and "всего" in log_text())

app.log.delete("1.0", "end")
check("Имена: Показать недостающие падежи", click(names, "Показать недостающие падежи")
      and run_and_wait() and ("pymorphy3" in log_text() or "падежные" in log_text().lower()))

app.log.delete("1.0", "end")
clean.f_utf8.var.set(str(CORPUS / "enc"))
clean.c_utf8_fix.var.set(False)
check("Чистка: Проверить кодировки (dry)", click(clean, "Проверить кодировки")
      and run_and_wait() and "ТОЛЬКО ОТЧЁТ" in log_text())

# витрина чистки штампов: чекбокс -> обзор -> диалог -> выбор -> применение
import customtkinter as _ctk
check("Хранилище: чекбокс «Выборочно (витрина)» есть", vault.c_pc_review is not None)
app.log.delete("1.0", "end")
# свежие штампы: предыдущие GUI-тесты уже вычистили corpus/stamps
st_gui = HERE / "_tmp_gui_review"
if st_gui.exists():
    shutil.rmtree(st_gui)  # регенерируемая тестовая папка
st_gui.mkdir()
(st_gui / "a.md").write_text(chr(10).join([
    "Стоит отметить, что всё хорошо.",
    "В современном мире тест."]), encoding="utf-8")
vault.f_pc.var.set(str(st_gui))
vault.c_pc_review.set(True)
click(vault, "Почистить штампы")
# ждём диалог (обзор идёт в фоновом потоке)
dlg = None
end = time.time() + 30
while time.time() < end:
    app.update()
    top = [w for w in app.winfo_children() if isinstance(w, _ctk.CTkToplevel)]
    if top:
        dlg = top[0]
        break
    time.sleep(0.05)
check("Хранилище: витрина открылась", dlg is not None)
if dlg:
    dlg.destroy()
    app.update()
vault.c_pc_review.set(False)

# HelpBox во всех вкладках
hb = sum(1 for frame in app.nb._tab_dict.values() for w in walk_all(frame) if isinstance(w, HelpBox))
check("HelpBox на каждой вкладке (5 шт.)", hb == 5, f"найдено {hb}")

# регресс 01.10: HelpBox переносится по ширине окна (не обрезается на 920px)
app.geometry("920x640")
app.update()
pump(400)
clipped = []
for frame in app.nb._tab_dict.values():
    for w in walk_all(frame):
        if isinstance(w, HelpBox):
            wl = float(w._body.cget("wraplength"))
            if wl > w.winfo_width() + 5:
                clipped.append((wl, w.winfo_width()))
check("HelpBox: wraplength <= ширины блока при 920px", not clipped, str(clipped[:2]))
app.geometry("1100x800")
app.update()

# регресс 01.10: BigButton перекрашивается при смене темы
from widgets_ctk import BigButton as _BB
bb = next(w for frame in app.nb._tab_dict.values() for w in walk_all(frame)
          if isinstance(w, _BB))
app._on_theme_change("light")
app.update()
light_ok = bb.cget("fg_color") == "#7c3aed"
app._on_theme_change("dark")
app.update()
dark_ok = bb.cget("fg_color") == "#8b5cf6"
check("BigButton: перекрашивается при смене темы", light_ok and dark_ok,
      f"light={bb.cget('fg_color') if not light_ok else 'ok'}")

app.destroy()

print(f"\n=== ИТОГО: {len(PASS)} PASS, {len(FAIL)} FAIL ===")
for n, d in FAIL:
    print(f"  FAIL: {n}  | {d}")
sys.exit(1 if FAIL else 0)
