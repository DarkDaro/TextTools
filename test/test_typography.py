"""
Юнит-тесты типографики (07.11): пунктуация, диапазоны, «?..»,
пробелы внутри кавычек, неразрывные пробелы (инициалы, сокращения,
число+слово) и режим вычитки --check.

Ключевой момент истории: «слово  -  слово» с двойными пробелами не
доходило до правила тире — пунктуация теперь работает ПЕРВЫЙ и
нормализует пробелы до остальных правил.

Запуск:  python -m pytest test/test_typography.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools import typography as ty

NB = "\u00A0"  # неразрывный пробел


def tr(text, **kw):
    new, counts = ty.transform_text(text, **kw)
    return new, counts


# --- пунктуация ---

def test_missing_space_after_comma():
    new, c = tr("Да,нет")
    assert new == "Да, нет"
    assert c["punct"] == 1


def test_space_before_punct_removed():
    new, c = tr("слово , слово")
    assert new == "слово, слово"
    assert c["punct"] == 1


def test_missing_space_after_period_uppercase():
    new, c = tr("Он ушёл.Свет погас")
    assert new == "Он ушёл. Свет погас"
    assert c["punct"] == 1


def test_initials_spread():
    new, c = tr("А.С.Пушкин писал")
    assert new == "А. С. Пушкин писал"
    assert c["punct"] == 2


def test_glued_abbreviations():
    new, _ = tr("Это так,т.е. потому что")
    assert new == "Это так, т. е. потому что"


def test_double_spaces_collapsed():
    new, c = tr("Тишина  стояла  кругом")
    assert new == "Тишина стояла кругом"
    assert c["punct"] == 2


def test_protection_time_and_versions():
    new, c = tr("в 12:30 версия 1.2.3 вышла")
    assert new == "в 12:30 версия 1.2.3 вышла"
    assert c["punct"] == 0


def test_protection_smiley():
    new, c = tr("улыбнулся :) и :))")
    assert new == "улыбнулся :) и :))"
    assert c["punct"] == 0


def test_table_pipe_alignment_untouched():
    new, c = tr("| 5  | десять |")
    assert new == "| 5  | десять |"
    assert c["punct"] == 0


def test_lower_case_after_period_untouched():
    # латиница/нижний регистр после точки не трогаются: сайты, файлы
    new, c = tr("пример.ру и сайт.com")
    assert new == "пример.ру и сайт.com"
    assert c["punct"] == 0


# --- тире и диапазоны ---

def test_dash_with_extra_spaces():
    # раньше сжимались пробелы ПОСЛЕ правила тире — тире терялось
    new, c = tr("слово  -  слово")
    assert new == "слово — слово"
    assert c["dash"] == 1


def test_year_range_hyphen_to_dash():
    new, c = tr("война 1941-1945 годов")
    assert new == "война 1941—1945 годов"
    assert c["dash"] == 1


def test_en_dash_range_to_em_dash():
    new, c = tr("страницы 10–15")
    assert new == "страницы 10—15"
    assert c["dash"] == 1


def test_phone_untouched():
    new, c = tr("телефон +7-912-345-67-89")
    assert new == "телефон +7-912-345-67-89"
    assert c["dash"] == 0


# --- многоточие ---

def test_question_three_dots():
    new, c = tr("Что?...")
    assert new == "Что?.."
    assert c["dots"] == 1


def test_exclamation_three_dots():
    new, _ = tr("Ну!...")
    assert new == "Ну!.."


def test_plain_dots_to_ellipsis():
    new, _ = tr("Подожди...")
    assert new == "Подожди…"


def test_question_two_dots_untouched():
    new, c = tr("Что?..")
    assert new == "Что?.."
    assert c["dots"] == 0


# --- кавычки ---

def test_spaces_inside_quotes_removed():
    new, c = tr("он произнёс « важная мысль »")
    assert new == "он произнёс «важная мысль»"
    assert c["quotes"] == 2


def test_dialogue_dash_inside_quotes_kept():
    new, c = tr("Он сказал: «— Пойдём.»")
    assert new == "Он сказал: «— Пойдём.»"
    assert c["quotes"] == 0


# --- неразрывные пробелы (только с nbsp=True) ---

def test_nbsp_initials():
    new, c = tr("И.И. Иванов вошёл", nbsp=True)
    assert new == f"И.{NB}И.{NB}Иванов вошёл"
    assert c["nbsp"] == 2


def test_nbsp_abbreviations():
    new, c = tr("и т.д. и др. факты", nbsp=True)
    assert new == f"и{NB}т.{NB}д. и{NB}др. факты"
    assert c["nbsp"] == 3


def test_nbsp_number_with_shortening():
    new, _ = tr("в 1812 году отдадим 5 тыс. руб.", nbsp=True)
    assert f"1812{NB}году" in new
    assert f"5{NB}тыс." in new


def test_nbsp_number_with_word():
    new, _ = tr("шли 10 лет до 12 марта", nbsp=True)
    assert f"10{NB}лет" in new
    assert f"12{NB}марта" in new


def test_nbsp_off_by_default():
    new, _ = tr("шли 10 лет в лесу", nbsp=False)
    assert NB not in new


# --- вычитка (--check) ---

def test_check_finds_problems():
    text = ("Он ушёл.Свет погас,\n"
            "она - убийца  1941-1945  \"правда\"?\n"
            "Тишина...  « эхо »")
    findings = ty.check_text(text)
    names = {n for _, n, _ in findings}
    for expected in ("нет пробела после знака", "прямые кавычки",
                     "двойной пробел", "дефис вместо тире",
                     "дефис в диапазоне лет", "многоточие из точек",
                     "пробел внутри кавычек"):
        assert expected in names, f"не найдено: {expected}"
    lines = {i for i, _, _ in findings}
    assert lines == {1, 2, 3}


def test_check_unpaired_quotes():
    findings = ty.check_text("обещание «сбылось")
    names = {n for _, n, _ in findings}
    assert "ёлочки без пары" in names


def test_check_skips_frontmatter_and_code():
    text = ('---\ntitle: не трогать "и --здесь"\n---\n'
            '```code --skip --me```\n'
            'Чисто. Всё в порядке.')
    assert ty.check_text(text) == []


def test_check_clean_text_empty():
    assert ty.check_text("Он ушёл. Свет погас.\nТишина.") == []


def test_check_inline_code_skipped():
    text = 'команда `--fix --nbsp` в порядке'
    assert ty.check_text(text) == []


def test_run_check_reports_and_keeps_files(tmp_path):
    f = tmp_path / "глава.txt"
    f.write_text("Он ушёл.Свет погас\n", encoding="utf-8")
    rep = tmp_path / "check.md"
    rc = ty.run_check(str(f), out=str(rep))
    assert rc == 0
    assert f.read_text(encoding="utf-8") == "Он ушёл.Свет погас\n"
    body = rep.read_text(encoding="utf-8")
    assert "нет пробела после знака" in body
    assert "строка 1" in body


def test_check_docx_finds_paragraph(tmp_path):
    from docx import Document
    doc = Document()
    doc.add_paragraph("Он ушёл.Свет погас")
    doc.add_paragraph("война 1941-1945 годов")
    p = tmp_path / "глава.docx"
    doc.save(p)
    findings = ty.check_docx(p)
    paras = {i for i, _, _ in findings}
    assert paras == {1, 2}
    names = {n for _, n, _ in findings}
    assert "нет пробела после знака" in names
    assert "дефис в диапазоне лет" in names


def test_fix_docx_applies_new_rules(tmp_path):
    from docx import Document
    doc = Document()
    doc.add_paragraph("Он ушёл.Свет погас.  Война 1941-1945 годов")
    p = tmp_path / "глава.docx"
    doc.save(p)
    counts = ty.fix_docx(p, nbsp=False, fix=True)
    assert counts["punct"] >= 1
    assert counts["dash"] >= 1
    after = Document(p).paragraphs[0].text
    assert "Он ушёл. Свет погас." in after
    assert "1941—1945" in after
