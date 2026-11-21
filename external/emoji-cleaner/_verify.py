# Проверка результатов чистки (не меняет файлы)
from docx import Document
from lxml import etree

# 1. docx: форматирование, таблица, сноска
doc = Document(r"C:\AgentLetta\python-projects\emoji-cleaner\test_fmt.docx")
p = doc.paragraphs[0]
for r in p.runs:
    print(f"run: {r.text!r} bold={r.bold} italic={r.italic}")
t = doc.tables[0]
print("ячейки:", t.rows[0].cells[0].text, "|", t.rows[0].cells[1].text,
      "|", t.rows[1].cells[0].text, "|", t.rows[1].cells[1].text)

# сноска: достаём из part-блоба
for rel in doc.part.rels.values():
    if "footnotes" in rel.reltype:
        root = etree.fromstring(rel.target_part.blob)
        for wt in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
            print("сноска:", repr(wt.text))

# 2. md: показать результат
print("--- test.md ---")
print(open(r"C:\AgentLetta\python-projects\emoji-cleaner\test.md", encoding="utf-8").read())
print("--- конец ---")