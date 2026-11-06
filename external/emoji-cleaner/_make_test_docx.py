# Тест: создание docx с форматированием, таблицей, сноской
from docx import Document
from docx.opc.part import Part
from docx.opc.packuri import PackURI

doc = Document()

# абзац с жирным и курсивом, эмодзи внутри форматированных run'ов
p = doc.add_paragraph()
r1 = p.add_run("Жирный ")
r1.bold = True
r2 = p.add_run("текст 🎉 и ")
r2.bold = True
r3 = p.add_run("курсив ✨")
r3.italic = True
r4 = p.add_run(" хвост без стиля :)")
doc.add_paragraph("Обычный абзац, чистый.")

# таблица 2x2 с эмодзи
t = doc.add_table(rows=2, cols=2)
t.rows[0].cells[0].text = "Ячейка ❌"
t.rows[0].cells[1].text = "Чистая"
t.rows[1].cells[0].text = "Вложенная 🎯"
t.rows[1].cells[1].text = "Тоже"

# добавляем часть footnotes вручную (python-docx их не создаёт)
FOOTNOTES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:footnote w:id="2"><w:p><w:r><w:rPr><w:i/></w:rPr>'
    '<w:t>Сноска с эмодзи 🎉 и смайлом :) - курсивная</w:t>'
    '</w:r></w:p></w:footnote></w:footnotes>'
).encode("utf-8")

part = Part(
    PackURI("/word/footnotes.xml"),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml",
    FOOTNOTES_XML,
    doc.part.package,
)
doc.part.relate_to(part, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes")

doc.save(r"C:\AgentLetta\python-projects\emoji-cleaner\test_fmt.docx")
print("test_fmt.docx создан")