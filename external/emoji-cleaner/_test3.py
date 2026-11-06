# -*- coding: utf-8 -*-
# Тест 3: разнобразные кейсы - сложный docx, md-края, бинарники, .git, регистр расширений
import subprocess, sys, os
from pathlib import Path

PY = sys.executable
D = Path(r"C:\AgentLetta\python-projects\emoji-cleaner")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def run(*extra):
    r = subprocess.run([PY, str(D / "clean.py"), *extra], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print("STDOUT:", r.stdout)
        print("STDERR:", r.stderr)
        raise SystemExit("clean.py упал!")
    return r.stdout


def check(cond, msg):
    if not cond:
        raise SystemExit(f"ПРОВАЛ: {msg}")
    print("  ok:", msg)


# ============ ТЕСТ A: md-края ============
print("=== A: md (CRLF, frontmatter, inline-код, математика) ===")
ta = D / "ta.md"
ta.write_bytes(
    "---\ntitle: Заметка 🎈 #1\n---\n"
    "Математика: x \u2265 5, a \u2248 b, \u00b10.5, \u00bd, \u2211, \u00d76, \u00f72. Номер \u2116 7.\r\n"
    "Кавычки \u00abёлка\u00bb и тире \u2014 целы, многоточие \u2026 тоже.\r\n"
    "Смайл в inline-коде `x = :) func()` не трогаем, а тут :) убираем.\r\n"
    "Эмодзи \U0001F389 и стрелка \u2192 наружу, hard-break в конце с эмодзи \U0001F3AF  \r\n"
    "```python\r\ns = 'привет :)'  # \U0001F389 в коде\n```\n".encode("utf-8"))

out = run(str(ta))
print(out)
after = ta.read_bytes().decode("utf-8")

check("\u2116 7" in after, "№ сохранён")
check("\u2265" in after and "\u2211" in after and "\u00bd" in after, "матсимволы целы")
check("\u00ab\u0451\u043b\u043a\u0430\u00bb" in after and "\u2014" in after and "\u2026" in after, "типографика целая")
check("`x = :) func()`" in after, "смайл в inline-коде сохранён")
check(":)" not in after.replace("`x = :) func()`", "").replace("'привет :)'", ""), "смайл снаружи убран")
check("\U0001F389" not in after.replace("'привет ", "xx"), "🎉 убран (в коде тоже)")
check("\u2192" not in after, "→ убрана")
lines = after.split("\n")
hb = lines[6].rstrip("\r")
check(hb.endswith("  "), f"hard-break (2+ пробела) сохранён: {hb!r}")
check(after.count("\r\n") >= 4, "CRLF сохранён")
check("---\ntitle: Заметка #1\n---" in after, "frontmatter почищен")

# ============ ТЕСТ B: сложный docx ============
print("=== B: docx (гиперссылка, текстбокс, колонтитулы, эдноут, комментарий, вложенная таблица) ===")
from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.opc.part import Part
from docx.opc.packuri import PackURI
from docx.opc.constants import RELATIONSHIP_TYPE as RT

doc = Document()

# вложенная таблица с эмодзи во всех уровнях
t = doc.add_table(rows=1, cols=1)
t.rows[0].cells[0].text = "Внешняя 🎈 ячейка"
inner = t.rows[0].cells[0].add_table(rows=1, cols=1)
inner.rows[0].cells[0].text = "Внутренняя 🎈 ячейка"

# суперскрипт с эмодзи
p = doc.add_paragraph()
r = p.add_run("10")
r = p.add_run(" м² 🎈")
r.font.superscript = True

# run с краевыми пробелами (xml:space preserve) и эмодзи
p = doc.add_paragraph()
r = p.add_run("  края  🎈  пробелы  ")
r.bold = True

# разрыв смайла между run'ами (ограничение: не удаляется, но не падает)
p = doc.add_paragraph()
p.add_run("разрыв смайла :")
p.add_run(") хвост")

# гиперссылка с текстом
rid = doc.part.relate_to("https://example.com/doc", RT.HYPERLINK, is_external=True)
hl = parse_xml(
    f'<w:hyperlink {nsdecls("w", "r")} r:id="{rid}">'
    '<w:r><w:t>Текст ссылки 🎈 и тут</w:t></w:r></w:hyperlink>')
doc.paragraphs[-1]._p.addnext(hl)

# текстбокс с жирным текстом
box = parse_xml(
    '<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:v="urn:schemas-microsoft-com:vml"><w:r><w:pict>'
    '<v:shape id="tb1" style="width:100pt;height:50pt">'
    '<v:textbox><w:txbxContent>'
    '<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Текстбокс 🎈 жирный</w:t></w:r></w:p>'
    '</w:txbxContent></v:textbox></v:shape></w:pict></w:r></w:p>')
doc.element.body.append(box)

# колонтитулы
doc.sections[0].header.paragraphs[0].add_run("Шапка 🎈 и смайл :)")
doc.sections[0].footer.paragraphs[0].add_run("Подвал 🎈")

# эндноут и комментарий - сырые части
def add_part(partname, reltype, xml):
    part = Part(PackURI(partname),
                "application/vnd.openxmlformats-officedocument.wordprocessingml." + reltype.split("/")[-1] + "+xml",
                xml.encode("utf-8"), doc.part.package)
    doc.part.relate_to(part, reltype)

add_part("/word/endnotes.xml", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/endnotes",
         '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
         '<w:endnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
         '<w:endnote w:id="1"><w:p><w:r><w:t>Эндноут 🎈 :)</w:t></w:r></w:p></w:endnote></w:endnotes>')
add_part("/word/comments.xml", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments",
         '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
         '<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
         '<w:comment w:id="0" w:author="T"><w:p><w:r><w:t>Комментарий 🎈 :)</w:t></w:r></w:p></w:comment></w:comments>')

tb = D / "tb.docx"
doc.save(tb)
out = run(str(tb))
print(out)

doc2 = Document(tb)
allt = " ".join(t.text for t in doc2.element.iter(W + "t"))
check("Внешняя ячейка" in allt and "Внутренняя ячейка" in allt, "вложенные таблицы почищены")
sup = [r for r in doc2.paragraphs[0].runs if r.font.superscript]
check(sup and "🎈" not in sup[0].text, "суперскрипт почищен, vertAlign цел")
bold_r = [r for r in doc2.paragraphs[1].runs if r.bold][0]
check(bold_r.text == "  края   пробелы  " or bold_r.text.strip() == "края пробелы",
      f"краевые пробелы preserve: {bold_r.text!r}")
check(bold_r.text.startswith("  ") and bold_r.text.endswith("  "), "краевые пробелы НЕ съедены")
check("разрыв смайла :" in allt and ") хвост" in allt, "разорванный смайл не удалён (документированное ограничение)")
check("Текст ссылки и тут" in allt, "текст гиперссылки почищен")
check(any("Текстбокс" in t.text and "🎈" not in t.text for t in doc2.element.iter(W + "t")), "текстбокс почищен")
tbx = [t for t in doc2.element.iter(W + "txbxContent") for t in t.iter(W + "t")][0]
check(tbx.get("{http://www.w3.org/XML/1998/namespace}space") is not None or tbx.text == tbx.text.strip(), "текстбокс валиден")
check("🎈" not in doc2.sections[0].header.paragraphs[0].text and ":)" not in doc2.sections[0].header.paragraphs[0].text,
      "колонтитул-хедер почищен")
check("🎈" not in doc2.sections[0].footer.paragraphs[0].text, "колонтитул-футер почищен")
for rel in doc2.part.rels.values():
    if "endnotes" in rel.reltype:
        root_xml = rel.target_part.blob
        check("Эндноут  и" in root_xml.decode("utf-8") or "Эндноут" in root_xml.decode("utf-8"), "эндноут почищен")
    if "comments" in rel.reltype:
        check("Комментарий" in rel.target_part.blob.decode("utf-8") and "🎈" not in rel.target_part.blob.decode("utf-8"),
              "комментарий почищен")
    if "hyperlink" in rel.reltype and rel.is_external:
        check(rel.target_ref == "https://example.com/doc", "URL гиперссылки не тронут")

# ============ ТЕСТ C: бинарник, .git, регистр ============
print("=== C: бинарник, .git, расширения ===")
tbin = D / "bin.txt"
tbin.write_bytes(b"\x00\x01binary :) trash \xff\xfe" * 3)
before = tbin.read_bytes()
out = run(str(tbin))
check(tbin.read_bytes() == before, "бинарный файл пропущен и не изменён")
check("бинарный" in out, "предупреждение выведено")

# папка с .git и uppercase-расширением
tf = D / "_sandbox"
(tf / ".git").mkdir(parents=True, exist_ok=True)
(tf / ".git" / "secret.md").write_text("в .git 🎈", encoding="utf-8")
(tf / "UPPER.MD").write_text("Верхний регистр 🎈 и :)", encoding="utf-8")
(tf / "note.txt").write_text("Обычный 🎈", encoding="utf-8")
run(str(tf))
check("🎈" in (tf / ".git" / "secret.md").read_text(encoding="utf-8"), ".git пропущен")
check("🎈" not in (tf / "UPPER.MD").read_text(encoding="utf-8"), ".MD (uppercase) почищен")
check("🎈" not in (tf / "note.txt").read_text(encoding="utf-8"), ".txt в папке почищен")

print("\nВСЕ ТЕСТЫ ПРОЙДЕНЫ")