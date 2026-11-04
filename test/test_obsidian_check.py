"""
Тест obsidian-check на фикстурах synthetic/13_obsidian_broken.

Проверяет две вещи:
  1. каждая поломка в фикстуре действительно находится (код на месте);
  2. --fix правит только машинно-однозначное, не трогает чистые файлы
     и склеивает посимвольный блок байт в байт.

Запуск:  python test/test_obsidian_check.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools import obsidian_check

FIXTURE = HERE / "synthetic" / "13_obsidian_broken"

# какой код обязан появиться на каком файле
EXPECTED = {
    "01_bad_frontmatter.md": {"FM_YAML"},
    "02_unclosed_fence.md": {"FENCE_UNCLOSED"},
    "03a_bad_sep.md": {"BAD_SEP"},
    "03b_extra_cells.md": {"TBL_COLS"},
    "03c_pipe_in_code.md": {"TBL_PIPE_IN_CODE"},
    "04_heading_issues.md": {"H_NO_SPACE", "H_EMPTY", "H_JUMP", "H_MULTI_H1"},
    "05_links.md": {"WIKI_BROKEN", "WIKI_ATTACH_MISSING", "MDLINK_BROKEN"},
    "06_tags.md": {"TAG_NUMERIC"},
    "07_exploded.md": {"EXPLODED"},
    "09_frontmatter_variants.md": {"FM_DESC", "FM_TAGS"},
    "10_no_description.md": {"FM_DESC"},
    "11_unclosed_frontmatter.md": {"FM_UNCLOSED"},
    "12_empty_wikilink.md": {"WIKI_EMPTY"},
}

# файл без поломок: после --fix его не должно быть в бэкапах
CLEAN = "08_clean.md"

# эталон: во что должен склеиться 07_exploded.md
EXPLODED_EXPECTED = """---
description: Посимвольно разбитый текст
---
# Развалина

## 18.09 08:30: ИТОГ ПО ПОЧИНКЕ

**Что дала эпопея (для будущего меня):**

- Self-parent — валидный lni-формат.
"""


def collect(folder):
    """{(имя файла, код)} — что нашёл валидатор."""
    files = list(obsidian_check.iter_md(folder))
    index = obsidian_check.build_index(files, Path(folder))
    found = set()
    for p in files:
        for _path, _line, code, _msg in obsidian_check.validate_file(p, index):
            found.add((p.name, code))
    return found


def check_detection():
    found = collect(FIXTURE)
    failures = []
    for name, codes in EXPECTED.items():
        for code in codes:
            if (name, code) not in found:
                failures.append("не найдено: %s -> %s" % (name, code))
    # чистая заметка не должна давать ничего кроме INFO
    bad_clean = {c for n, c in found
                 if n == CLEAN and obsidian_check.SEVERITY.get(c) in ("ERROR", "WARN")}
    if bad_clean:
        failures.append("чистая заметка дала %s" % sorted(bad_clean))
    return failures, found


def check_fix():
    failures = []
    tmp = Path(tempfile.mkdtemp(prefix="obsidian_fix_"))
    try:
        work = tmp / "vault"
        shutil.copytree(FIXTURE, work)
        before = {p.name: p.read_text(encoding="utf-8") for p in work.glob("*.md")}

        original_run = obsidian_check.run
        try:
            obsidian_check.run(str(work), fix=True, out=None)
        finally:
            obsidian_check.run = original_run

        # 1) посимвольный блок склеен байт в байт (хвостовой перевод строки допустим)
        fixed = (work / "07_exploded.md").read_text(encoding="utf-8")
        if fixed.rstrip("\n") != EXPLODED_EXPECTED.rstrip("\n"):
            failures.append("07_exploded.md склеен неверно:\n%r" % fixed[:300])

        # 2) чистый файл не тронут и бэкапа у него нет
        if (work / (CLEAN + ".bak")).exists():
            failures.append("%s получил .bak хотя правок не требовал" % CLEAN)
        if (work / CLEAN).read_text(encoding="utf-8") != before[CLEAN]:
            failures.append("%s изменён" % CLEAN)

        # 3) у каждого изменённого файла есть .bak
        for name, text in before.items():
            now = (work / name).read_text(encoding="utf-8")
            if now != text:
                if not (work / (name + ".bak")).exists():
                    failures.append("%s изменён без .bak" % name)

        # 4) после fix исчезли ровно те коды, которые чинятся автоматом
        found = {c for _n, c in collect(work)}
        for gone in ("FM_YAML", "EXPLODED", "TBL_PIPE_IN_CODE"):
            if gone in found:
                failures.append("%s не исчез после --fix" % gone)
        # а неисправимое осталось на месте
        for stay in ("FENCE_UNCLOSED", "H_NO_SPACE", "FM_UNCLOSED", "WIKI_BROKEN",
                     "BAD_SEP", "TBL_COLS"):
            if stay not in found:
                failures.append("%s пропал, хотя --fix его не чинит" % stay)

        # 5) идемпотентность: второй прогон не должен ничего менять
        snapshot = {p.name: p.read_bytes() for p in work.glob("*.md")}
        baks_before = {p.name for p in work.glob("*.bak")}
        obsidian_check.run(str(work), fix=True, out=None)
        for name, data in snapshot.items():
            if (work / name).read_bytes() != data:
                failures.append("второй --fix изменил %s (не идемпотентно)" % name)
        extra = {p.name for p in work.glob("*.bak")} - baks_before
        if extra:
            failures.append("второй --fix создал лишние .bak: %s" % sorted(extra))

        # 6) --no-bak не оставляет бэкапов
        work2 = tmp / "vault_nobak"
        shutil.copytree(FIXTURE, work2)
        obsidian_check.run(str(work2), fix=True, out=None, no_bak=True)
        if list(work2.glob("*.bak")):
            failures.append("--no-bak всё равно создал .bak")

        # 7) код возврата: 1 при найденных ERROR, 0 с --exit-zero
        code = obsidian_check.run(str(work2), out=None)
        if code != 1:
            failures.append("на ERROR код возврата %d, ожидался 1" % code)
        code = obsidian_check.run(str(work2), out=None, exit_zero=True)
        if code != 0:
            failures.append("с --exit-zero код %d, ожидался 0" % code)

        # 8) чистый vault не падает и даёт код 0 (был StopIteration)
        clean = tmp / "clean_vault"
        clean.mkdir()
        (clean / "ok.md").write_text(
            "---\ndescription: Чистая заметка\n---\n# Заголовок\n\n## Раздел\n",
            encoding="utf-8")
        try:
            code = obsidian_check.run(str(clean), out=None)
        except Exception as e:
            failures.append("чистый vault: исключение %r" % e)
            code = None
        if code not in (0, None):
            failures.append("чистый vault дал код %d, ожидался 0" % code)

        # 9) блок пустых строк не считается посимвольным развалом
        if obsidian_check.find_exploded_runs([""] * 60):
            failures.append("60 пустых строк приняты за развалину")

        # 10) у ссылок есть номер строки
        fixture_files = list(obsidian_check.iter_md(FIXTURE))
        fixture_index = obsidian_check.build_index(fixture_files, FIXTURE)
        links = [r for p in fixture_files
                 for r in obsidian_check.validate_file(p, fixture_index)
                 if r[2] in ("WIKI_BROKEN", "MDLINK_BROKEN", "WIKI_ATTACH_MISSING")]
        if not links or any(r[1] <= 0 for r in links):
            failures.append("у замечаний по ссылкам нет номера строки: %s"
                            % [(r[2], r[1]) for r in links][:5])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return failures


def main():
    failures, found = check_detection()
    print("Найдено замечаний: %d" % len(found))
    failures += check_fix()
    if failures:
        print("\nПРОВАЛ (%d):" % len(failures))
        for f in failures:
            print("  -", f)
        return 1
    print("OK: все поломки находятся, --fix правит только однозначное")
    return 0


if __name__ == "__main__":
    sys.exit(main())
