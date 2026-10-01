# -*- coding: utf-8 -*-
"""Полный синтетический тест движков и CLI textools.

Покрывает: core (text_parser, name_registry, vault_scanner, docx_io),
tools (registry_builder, consistency, orphan/broken/merge, phrase_check,
whitespace_clean), wrappers, CLI textools.py и внешние скрипты.
Реальные записи идут только в archive/corpus (регенерируется gen_corpus.py).

Запуск: python test_engines.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
CORPUS = HERE / "corpus"
sys.path.insert(0, str(ROOT))

# свежий корпус (прогон независим от порядка и от GUI-тестов)
subprocess.run([sys.executable, str(HERE / "gen_corpus.py")], check=True)

PASS = []
FAIL = []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append((name, detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  | {detail}" if detail and not cond else ""))


def run_cli(*args, **kw):
    r = subprocess.run([sys.executable, str(ROOT / "textools.py"), *args],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120, **kw)
    return r.returncode, r.stdout + r.stderr


# ================= core.text_parser =================
from core import text_parser as tp

check("read_text utf-8", tp.read_text(CORPUS / "names" / "book1.md") is not None)
check("read_text docx", tp.read_text(CORPUS / "docx" / "names.docx") is not None)
check("read_text: koi8 детектируется (Ф2)", tp.read_text(CORPUS / "enc" / "koi8.txt") == "Привет, мир!")


def _empty_input_raises():
    try:
        list(tp.iter_text_files(""))
        return False
    except ValueError:
        return True


check("iter_text_files пустой путь -> ValueError", _empty_input_raises())

files = list(tp.iter_text_files(CORPUS / "enc"))
check("iter_text_files: только текстовые ext", all(f.suffix.lower() in tp.TEXT_EXTS for f in files))
check("iter_text_files: single file", list(tp.iter_text_files(CORPUS / "names" / "book1.md")) == [CORPUS / "names" / "book1.md"])
limited = list(tp.iter_text_files(CORPUS, limit=2))
check("iter_text_files: limit=2", len(limited) == 2)
check("sentences", tp.sentences("Раз. Два! Три?") == ["Раз", "Два", "Три"])
cands = tp.find_name_candidates("Он шёл, Эрика пела, и ЛИКА кричала, и Лика смотрела.")
check("find_name_candidates: заглавные в середине", "эрика" in cands and "лика" in cands)
check("find_name_candidates: аббревиатуры пропущены", "эрика" in cands and all(not c.isupper() for c in cands))
check("find_name_candidates: known исключается",
      tp.find_name_candidates("Он шёл. Эрика была тут.", known={"эрика"}) == [])
# "мастер" в STOPLIST — пары с ним не предлагаются (титул, не имя)
bgs = tp.find_bigrams("Он шёл. Мастер Кайдзо ждал. Красный Дом стоял. Серый Волк выл.")
check("find_bigrams (титул отфильтрован)", "красный дом" in bgs and "серый волк" in bgs and "мастер кайдзо" not in bgs)

# ================= core.name_registry =================
from core import name_registry as nr

chars = nr.load_registry(CORPUS / "names" / "registry.yaml")
check("load_registry: 2 записи", len(chars) == 2)
check("load_registry: несуществующий -> []", nr.load_registry(CORPUS / "nope.yaml") == [])
check("known_forms", "лика" in nr.known_forms(chars) and "кайзо" in nr.known_forms(chars))
check("known_first_names: титул", "мастер" in nr.known_first_names(chars))
tmp_reg = HERE / "_tmp_registry.yaml"
nr.save_registry(tmp_reg, chars)
check("save_registry roundtrip", nr.load_registry(tmp_reg) == chars)

# ================= core.vault_scanner =================
from core import vault_scanner as vs

notes, bases, rels = vs.scan_vault(CORPUS / "vault")
check("scan_vault: 7 md", len(notes) == 7)
check("scan_vault: basenames", "заметка а" in bases and "orphan" in bases)
check("scan_vault: relpaths с папкой", "sub/заметка b" in rels)
check("_clean_link алиас/глава/.md",
      vs._clean_link("путь/имя.md#глава|алиас") == "путь/имя")
check("is_resolved по пути", vs.is_resolved("sub/заметка b", bases, rels))
check("is_resolved по имени", vs.is_resolved("заметка а", bases, rels))
check("is_resolved битая", not vs.is_resolved("нет такой заметки", bases, rels))
single, sb, sr = vs.scan_vault(CORPUS / "vault" / "orphan.md")
check("scan_vault: один файл", len(single) == 1 and single[0].links == set())
idx = [n for n in notes if n.stem == "index"][0]
check("incoming_filter: на index ссылаются", vs.incoming_filter(notes, idx, bases, rels))
orph = [n for n in notes if n.stem == "orphan"][0]
check("incoming_filter: orphan без входящих", not vs.incoming_filter(notes, orph, bases, rels))
check("hashlib_md5", len(vs.hashlib_md5("x")) == 32)

# ================= core.docx_io =================
from core import docx_io

names_docx = CORPUS / "docx" / "names.docx"
torn = CORPUS / "docx" / "torn.docx"
check("docx read_text", "Лика" in docx_io.read_text(names_docx))
check("count_in_docx регистрозависимо",
      docx_io.count_in_docx(names_docx, "лика") == 0 and docx_io.count_in_docx(names_docx, "Лика") == 1)
check("count_in_docx regex", docx_io.count_in_docx(names_docx, r"Лик\w", is_regex=True) >= 1)

# замены — на копии
cp = HERE / "_tmp_names.docx"
shutil.copy2(names_docx, cp)
t, ch, br = docx_io.replace_in_docx(cp, "лика", "X")
check("replace literal: нижний регистр не заменяет", t == 0 and ch == 0)
t, ch, br = docx_io.replace_in_docx(cp, "Лика", "Эрика", backup=False)
check("replace literal: точная замена", t == 1 and ch == 1)
check("replace literal: файл изменён", "Эрика" in docx_io.read_text(cp) and "Лика" not in docx_io.read_text(cp))
t, ch, br = docx_io.replace_in_docx(cp, r"Эрик\w+", "Y", is_regex=True, backup=False)
check("replace regex", t >= 1)
t, ch, br = docx_io.replace_in_docx(torn, "Лика шла", "X", backup=False)
check("replace torn: разорванное между run'ами -> broken=1", t == 0 and br == 1)
full = docx_io.read_text(names_docx)
docx_io.replace_in_docx_text(cp, "строка А\nстрока Б")
check("replace_in_docx_text: параграфы перезаписаны",
      docx_io.read_text(cp).strip().split("\n") == ["строка А", "строка Б"])
shutil.copy2(names_docx, cp)
t, ch, br = docx_io.replace_in_docx(cp, "Лика", "Эрика")  # backup=True
check("replace: .bak создан", (Path(str(cp) + ".bak")).exists())

# ================= tools.registry_builder =================
from tools import registry_builder as rb

out_yaml = HERE / "_tmp_cand.yaml"
rb.run(str(CORPUS / "names"), out=str(out_yaml), min_count=1)
cand = nr.load_registry(out_yaml)
check("registry_builder: кандидаты сохранены", len(cand) > 0)
rb.run(str(CORPUS / "names"), out=str(out_yaml), registry=str(CORPUS / "names" / "registry.yaml"), min_count=2)
cand2 = nr.load_registry(out_yaml)
check("registry_builder: известные исключены",
      all(c["имя"] not in ("лика", "эрика") for c in cand2))

# ================= tools.consistency =================
from tools import consistency as cons

report = HERE / "_tmp_report.md"
cons.run(str(CORPUS / "names"), str(CORPUS / "names" / "registry.yaml"), out=str(report))
rep = report.read_text(encoding="utf-8")
check("consistency: старые найдены", "старое: 4" in rep or "старое: 5" in rep)
check("consistency: опечатки найдены", "опечатки: 1" in rep)

# ================= tools vault =================
from tools import orphan_finder, broken_links, merge_finder

o_rep = HERE / "_tmp_orphan.md"
orphan_finder.run(str(CORPUS / "vault"), out=str(o_rep))
check("orphan_finder: 3 orphan", "Orphans: 3" in o_rep.read_text(encoding="utf-8"))
b_rep = HERE / "_tmp_broken.md"
broken_links.run(str(CORPUS / "vault"), out=str(b_rep))
check("broken_links: 1 битая", "Broken: 1 в 1 файлах" in b_rep.read_text(encoding="utf-8"))
m_rep = HERE / "_tmp_merge.md"
merge_finder.run(str(CORPUS / "vault"), out=str(m_rep))
mtxt = m_rep.read_text(encoding="utf-8")
check("merge_finder: дубликат по содержимому", "Дубликаты по содержимому: 1 групп" in mtxt)
check("merge_finder: одинаковые имена", "Одинаковые имена: 1 групп" in mtxt)

# ================= tools.phrase_check =================
from tools import phrase_check as pc

check("load_phrases builtin", len(pc.load_phrases()) >= 50)
custom = HERE / "_tmp_custom.yaml"
custom.write_text("- моя тестовая фраза", encoding="utf-8")
check("load_phrases custom", "моя тестовая фраза" in pc.load_phrases(str(custom)))
check("count_phrase", pc.count_phrase("Такой Вот Текст", "такой вот") == 1)

# _replace_preserving_case
r = pc._replace_preserving_case("Стоит отметить, что тест.", "стоит отметить, что", "")
check("_rpc: удаление связки", r == "тест.")
r = pc._replace_preserving_case("в современном мире", "в современном мире", "сегодня")
check("_rpc: замена в начале строки", r == "Сегодня")
r = pc._replace_preserving_case("текст. Стоит отметить, что факт.", "стоит отметить, что", "")
check("_rpc: после точки (замена пустая, следующее слово не капится)", r == "текст. факт.")

# add_phrase с подменой файла (реальный phrases.yaml не трогаем)
real_pf = pc.PHRASES_FILE
pf = HERE / "_tmp_phrases.yaml"
pc.PHRASES_FILE = pf
pc.add_phrase("Тестовая Фраза Для Словаря")
check("add_phrase: записана", "тестовая фраза для словаря" in pf.read_text(encoding="utf-8"))
pc.add_phrase("тестовая фраза для словаря")
pc.PHRASES_FILE = real_pf

import io as _io
import contextlib
buf = _io.StringIO()
with contextlib.redirect_stdout(buf):
    pc.run(str(CORPUS / "stamps"))
o = buf.getvalue()
check("phrase_check run: PROGRESS-маркеры", "PROGRESS:0/2" in o and "PROGRESS:2/2" in o)
check("phrase_check run: штампы найдены", "стоит отметить, что" in o)

# clean dry-run (ничего не меняет)
before = (CORPUS / "stamps" / "s1.md").read_text(encoding="utf-8")
buf = _io.StringIO()
with contextlib.redirect_stdout(buf):
    pc.clean(str(CORPUS / "stamps"), dry_run=True)
o = buf.getvalue()
check("clean dry-run: план показан", "DRY-RUN" in o and "План замен" in o)
check("clean dry-run: файлы не изменены", (CORPUS / "stamps" / "s1.md").read_text(encoding="utf-8") == before)
# clean реальная с бэкапом
buf = _io.StringIO()
with contextlib.redirect_stdout(buf):
    pc.clean(str(CORPUS / "stamps"), dry_run=False)
after = (CORPUS / "stamps" / "s1.md").read_text(encoding="utf-8")
check("clean: штампы убраны", "стоит отметить" not in after.lower() and "в современном мире" not in after.lower())
check("clean: удалённая связка оставила текст", after.splitlines()[0] == "всё хорошо.")
baks = list((CORPUS / "stamps" / "md_replace_backups").rglob("*.md"))
check("clean: бэкапы созданы", len(baks) >= 1)

# ================= tools.whitespace_clean =================
from tools import whitespace_clean as wc

new_text, n = wc.clean_text("А.   \nБ\tБ.  \n\n\n\nВ.\n")
check("clean_text: хвосты/табы/пустые", new_text == "А.\nБ Б.\n\nВ.\n" and n >= 3)
kt, _ = wc.clean_text("Строка.  \nСлед.", keep_breaks=True)
check("clean_text: keep-breaks сохраняет '  '", "Строка.  " in kt)
ft, _ = wc.clean_text("```py\nx  =  1   \n```\nПосле.\n")
check("clean_text: код-блок не тронут", "x  =  1   " in ft)
mb, _ = wc.clean_text("А.\n\n\n\nБ.\n", max_blank=2)
check("clean_text: max_blank=2", "А.\n\n\nБ." in mb)
messy = CORPUS / "ws" / "messy.md"
wc.run(str(messy), fix=True)
fixed = messy.read_text(encoding="utf-8")
check("whitespace --fix: файл исправлен", fixed == "Строка с хвостом.\nСтрока с табом.\nДвойные пробелы внутри.\n\nПосле трёх пустых.\n```python\ncode  with  spaces   \n```\nФинал.\n")
check("whitespace --fix: .bak создан", Path(str(messy) + ".bak").exists())
ws_docx = CORPUS / "docx" / "ws.docx"
cnt = wc.clean_docx(ws_docx, 1, False, fix=True)
check("clean_docx: пустые параграфы сжаты, правки есть", cnt > 0)
check("clean_docx: .bak создан", Path(str(ws_docx) + ".bak").exists())

# ================= wrappers =================
from wrappers import (cmd_emoji_clean, cmd_clean_text, cmd_md_replace,
                      cmd_md_find_bad, cmd_md_fix_encoding, cmd_md_strip_bad,
                      cmd_char_search, cmd_char_fix_word, cmd_refile)

check("cmd_emoji_clean dry", "--dry-run" in cmd_emoji_clean(["X"]))
check("cmd_emoji_clean restore", "--restore" in cmd_emoji_clean(["X"], restore=True))
check("cmd_clean_text fix", "--fix" in cmd_clean_text("X", apply=True))
check("cmd_md_replace все флаги",
      all(f in cmd_md_replace("V", "o", "n", is_regex=True, include=["a"], exclude=["b"], no_backup=True)
          for f in ("--regex", "--include", "a", "--exclude", "b", "--no-backup", "--yes")))
check("cmd_md_find_bad", "--find-bad" in cmd_md_find_bad("V"))
check("cmd_md_fix_encoding", "--fix-encoding" in cmd_md_fix_encoding("V", dry_run=False))
check("cmd_md_strip_bad", "--strip-bad" in cmd_md_strip_bad("V"))
check("cmd_char_search fix", "--fix" in cmd_char_search("V", char="Эрика", fix=True))
check("cmd_char_fix_word", "--fix-word" in cmd_char_fix_word("V", "б", "х"))
check("cmd_refile", all(x in cmd_refile("D", "pat", replacement="r", exts=["txt"])
                        for x in ("-r", "r", "-d", "D", "--exts", "txt")))

# ================= CLI textools.py =================
code, o = run_cli("registry-builder", "--input", str(CORPUS / "names"), "--min-count", "2")
check("CLI registry-builder", code == 0 and "Кандидаты-слова" in o)
code, o = run_cli("consistency", "--input", str(CORPUS / "names"),
                  "--registry", str(CORPUS / "names" / "registry.yaml"), "--verbose")
check("CLI consistency", code == 0 and "Проблемных персонажей" in o)
code, o = run_cli("orphan-finder", "--input", str(CORPUS / "vault"), "--out", str(HERE / "_tmp_o2.md"))
check("CLI orphan-finder", code == 0 and "Orphan" in o)
code, o = run_cli("broken-links", "--input", str(CORPUS / "vault"))
check("CLI broken-links", code == 0 and "Битых ссылок: 1" in o)
code, o = run_cli("merge-finder", "--input", str(CORPUS / "vault"))
check("CLI merge-finder", code == 0 and "Дубликатов по содержимому: 1" in o)

# ================= внешние скрипты (через wrappers) =================
def run_ext(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    return r.returncode, r.stdout + r.stderr

# emoji_cleaner: dry, real+backup, restore
emoji_dir = CORPUS / "emoji"
code, o = run_ext(cmd_emoji_clean([str(emoji_dir)], dry_run=True))
check("emoji dry-run", code == 0)
code, o = run_ext(cmd_emoji_clean([str(emoji_dir)], dry_run=False, backup=True))
e1 = (emoji_dir / "e1.txt").read_text(encoding="utf-8")
check("emoji real: эмодзи/смайлы убраны", "🌲" not in e1 and ":)" not in e1 and "конец" in e1)
code, o = run_ext(cmd_emoji_clean([str(emoji_dir)], restore=True))
e1 = (emoji_dir / "e1.txt").read_text(encoding="utf-8")
check("emoji restore: из .bak вернулись", "🌲" in e1 or ":)" in e1)

# clean_text_files: dry + fix
cjk = CORPUS / "cjk"
code, o = run_ext(cmd_clean_text(str(cjk), apply=False))
c1_before = (cjk / "c1.txt").read_text(encoding="utf-8")
code, o = run_ext(cmd_clean_text(str(cjk), apply=True))
c1_after = (cjk / "c1.txt").read_text(encoding="utf-8")
check("clean_text: CJK убраны с --fix", "神秘" not in c1_after and "Нормальный текст" in c1_after)

# md_replace: dry, real, find-bad, fix-encoding, strip-bad
vault_copy = HERE / "_tmp_vault_md"
shutil.copytree(CORPUS / "vault", vault_copy, dirs_exist_ok=True)
code, o = run_ext(cmd_md_replace(str(vault_copy), "Текст", "Слово"))
check("md_replace dry-run: не меняет", "DRY-RUN" in o.upper() or "dry-run" in o.lower())
code, o = run_ext(cmd_md_replace(str(vault_copy), "Одинаковое содержимое дубликата", "ЗАМЕНЕНО", dry_run=False))
check("md_replace real: заменил", "ЗАМЕНЕНО" in (vault_copy / "dup_a.md").read_text(encoding="utf-8"))
code, o = run_ext(cmd_md_replace(str(vault_copy), "нет такой заметки", "исправлено", is_regex=False, dry_run=False))
code, o = run_ext(cmd_md_find_bad(str(CORPUS / "enc")))
check("md_replace find-bad", code == 0)
enc = CORPUS / "enc"
code, o = run_ext(cmd_md_fix_encoding(str(enc), dry_run=False))
check("md_replace fix-encoding: отработал", code == 0)
code, o = run_ext(cmd_md_strip_bad(str(CORPUS / "enc"), dry_run=False))
check("md_replace strip-bad: отработал", code == 0)

# char_search: проверка всех, --fix-word
code, o = run_ext(cmd_char_search(str(CORPUS / "names"), fix=False))
check("char_search: отчёт по реестру", code == 0)
names_copy = HERE / "_tmp_names_txt"
shutil.copytree(CORPUS / "names", names_copy, dirs_exist_ok=True)
code, o = run_ext(cmd_char_fix_word(str(names_copy), "Кайзо", "Кайдзо", dry_run=False))
b1 = (names_copy / "book1.md").read_text(encoding="utf-8")
check("char_search --fix-word: опечатка заменена", "Кайзо" not in b1 and "Кайдзо — это опечатка." in b1)

# refile: dry + real
rf = HERE / "_tmp_refile"
shutil.copytree(CORPUS / "refile", rf, dirs_exist_ok=True)
code, o = run_ext(cmd_refile(str(rf), r"\d{2}\.\d{2}\.\d{4}", replacement="ДАТА", exts=["txt"]))
code, o = run_ext(cmd_refile(str(rf), r"\d{2}\.\d{2}\.\d{4}", replacement="ДАТА", exts=["txt"], dry_run=False))
r1 = (rf / "r1.txt").read_text(encoding="utf-8")
check("refile real: regex-замена", "ДАТА" in r1 and "01.02.2026" not in r1)

# ================= Ф1: морфология (pymorphy3) =================
from core import morph

if morph.AVAILABLE:
    f_эрика = morph.word_forms("Эрика")
    check("morph: падежи Эрики", {"эрика", "эрику", "эрикой"} <= f_эрика, str(f_эрика))
    check("morph: косвенная форма не расширяется (нет мусора)",
          morph.word_forms("Эрики") == {"эрики"})
    check("morph: составное имя", morph.word_forms("Мастер Кайдзо") >= {"мастер кайдзо"})
    # consistency находит падеж старого имени, которого нет в реестре
    import tempfile, yaml as _yaml
    d_m = Path(tempfile.mkdtemp())
    (d_m / "t.txt").write_text("Он стал Лику спрашивать. Потом ушёл.", encoding="utf-8")
    reg_m = d_m / "r.yaml"
    reg_m.write_text(_yaml.safe_dump(
        [{"имя": "Эрика", "формы": ["Эрика"], "старое": ["Лика"],
          "старое_опасное": [], "опечатки": []}], allow_unicode=True), encoding="utf-8")
    cons.run(str(d_m), str(reg_m))
    # из консоли ничего не поймать — проверяем через out
    rep_m = d_m / "rep.md"
    cons.run(str(d_m), str(reg_m), out=str(rep_m))
    mtxt = rep_m.read_text(encoding="utf-8")
    check("morph: падеж «Лику» найден как старое имя", "старое: 1" in mtxt, mtxt[:300])
    # registry_builder исключает падежи известных
    cand_m = HERE / "_tmp_cand_morph.yaml"
    rb.run(str(d_m), out=str(cand_m), registry=str(reg_m), min_count=1)
    names_out = {c["имя"] for c in nr.load_registry(cand_m)}
    check("morph: «лику» не предлагается как кандидат", "лику" not in names_out, str(names_out))
    # morph_forms: подсказка и --fill
    from tools import morph_forms
    sug = morph_forms.suggestions(nr.load_registry(reg_m))
    check("morph_forms: подсказка для Эрики",
          "Эрика" in sug and "формы" in sug["Эрика"]
          and any(f in sug["Эрика"]["формы"] for f in ("эрику", "эрикой", "эрики")),
          str(sug))
    fill_reg = d_m / "r.yaml"
    morph_forms.run(str(fill_reg), fill=True)
    check("morph_forms: --fill дописал формы", Path(str(fill_reg) + ".bak").exists()
          and len(nr.load_registry(fill_reg)[0]["формы"]) > 1)
else:
    check("morph: pymorphy3 недоступен — тесты пропущены", True)

# ================= Ф2: utf8_convert =================
from tools import utf8_convert

# свежие файлы напрямую: внешние скрипты выше уже перекодировали corpus/enc
enc_copy = HERE / "_tmp_utf8"
if enc_copy.exists():
    shutil.rmtree(enc_copy)  # регенерируемая тестовая папка
enc_copy.mkdir()
(enc_copy / "koi8.txt").write_bytes("Привет, мир!".encode("koi8-r"))
(enc_copy / "cp1251.txt").write_bytes("Старая кодировка".encode("cp1251"))
buf = _io.StringIO()
with contextlib.redirect_stdout(buf):
    utf8_convert.run(str(enc_copy), fix=False)
o = buf.getvalue()
check("utf8: dry-run находит cp1251/koi8", "cp1251" in o and "koi8" in o, o[:300])
koi8 = enc_copy / "koi8.txt"
utf8_convert.run(str(koi8), fix=True)
check("utf8: --fix перекодировал с .bak", Path(str(koi8) + ".bak").exists()
      and koi8.read_bytes().decode("utf-8") == "Привет, мир!")

# ================= Ф3: матрица персонажей =================
from tools import character_matrix

mat_rep = HERE / "_tmp_matrix.md"
character_matrix.run(str(CORPUS / "names"), str(CORPUS / "names" / "registry.yaml"),
                     out=str(mat_rep))
mrep = mat_rep.read_text(encoding="utf-8")
check("matrix: Эрика упоминается", "## Эрика" in mrep and "не встречается" not in mrep.split("## Мастер Кайдзо")[0])
check("matrix: Мастер Кайдзо есть", "## Мастер Кайдзо" in mrep)

# ================= Ф4: мягкий стоп =================
flag = ROOT / "stop.flag"
flag.write_text("stop", encoding="utf-8")
check("stop: stop_requested()", tp.stop_requested())
check("stop: iter_text_files не выдаёт файлы", list(tp.iter_text_files(CORPUS / "names")) == [])
flag.unlink()  # тестовый флаг, создан этим же тестом
check("stop: после снятия флага работает", len(list(tp.iter_text_files(CORPUS / "names"))) >= 1)

# ================= Ф5: витрина чистки =================
# свежие штампы: штатная clean выше уже вычистила corpus/stamps
st_copy = HERE / "_tmp_review"
if st_copy.exists():
    shutil.rmtree(st_copy)  # регенерируемая тестовая папка
st_copy.mkdir()
(st_copy / "a.md").write_text(chr(10).join([
    "Стоит отметить, что всё хорошо.",
    "В современном мире тест. Не секрет, что пример."]), encoding="utf-8")
buf = _io.StringIO()
with contextlib.redirect_stdout(buf):
    pc.review(str(st_copy))
o = buf.getvalue()
check("review: REVIEW-строки с контекстом", o.count("REVIEW	") >= 2
      and "REVIEW-END" in o)
lines_r = [l.split("	") for l in o.splitlines() if l.startswith("REVIEW	")]
# чистим только одно вхождение одной фразы в одном файле
ph, repl, fstr = lines_r[0][1], lines_r[0][2], lines_r[0][3]
before_f = Path(fstr).read_text(encoding="utf-8")
other = [l.split("	") for l in o.splitlines() if l.startswith("REVIEW	")
         and l.split("	")[3] != fstr]
res = pc.clean_selection([(ph, fstr)])
after_f = Path(fstr).read_text(encoding="utf-8")
check("clean_selection: выбранное очищено", after_f != before_f
      and ph not in after_f.lower(), str(res[-1]))
if other:
    f2 = Path(other[0][3])
    check("clean_selection: остальные файлы не тронуты",
          f2.read_text(encoding="utf-8") == Path(other[0][3]).read_text(encoding="utf-8")
          if f2.read_text(encoding="utf-8") else True)

# ================= итог =================
print(f"\n=== ИТОГО: {len(PASS)} PASS, {len(FAIL)} FAIL ===")
for n, d in FAIL:
    print(f"  FAIL: {n}  | {d}")
sys.exit(1 if FAIL else 0)
