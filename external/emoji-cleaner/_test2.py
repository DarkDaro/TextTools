# Тест улучшений (самопроверка через subprocess-запуски clean.py)
import subprocess, sys
from pathlib import Path

PY = sys.executable
D = Path(r"C:\AgentLetta\python-projects\emoji-cleaner")

# 1. защита легитимных символов + hard-break
t2 = D / "test2.md"
t2.write_text(
    "Шахматы: конь b1-c3, фигура ♞ и пешка ♙. Ноты: до-мажор ♪ и ♫. "
    "Карты: ♠ ♥ ♦ ♣. Кости: ⚀ ⚃. Музыка не тронута ♩.\n"
    "А вот мусор: 🎉 ✅ ❌ → ▪ ⭐ ⌛ надо убрать. Смайл :) тоже.\n"
    "Строка с hard-break  \nвторая строка с эмодзи 🎯 и пробелами в  середине.\n",
    encoding="utf-8")

r = subprocess.run([PY, str(D / "clean.py"), str(t2)], capture_output=True, text=True)
print(r.stdout)

after = t2.read_text(encoding="utf-8")
assert "♞" in after and "♙" in after, "шахматы сломаны!"
assert "♪" in after and "♫" in after and "♩" in after, "ноты сломаны!"
assert "♠" in after and "♥" in after and "♦" in after and "♣" in after, "масти сломаны!"
assert "⚀" in after and "⚃" in after, "кости сломаны!"
assert "🎉" not in after and "✅" not in after and "→" not in after, "эмодзи не удалены!"
assert "🙂" not in after and ":)" not in after, "смайл не удалён!"
# hard-break: строка 1 после чистки всё ещё кончается двумя пробелами
l1 = after.split("\n")[0]
assert l1.endswith("  ") or l1 == l1.rstrip(), f"hard-break сломан: {l1!r}"
l3 = after.split("\n")[2]
assert l3.endswith("  "), f"hard-break удалён (2 пробела в конце строки 3): {l3!r}"
print("ТЕСТ 1 пройден: защита символов + hard-break")

# 2. dry-run превью + файл не изменён
t3 = D / "test3.md"
t3.write_text("Превью 💡 эмодзи 🚀 и смайла ;)", encoding="utf-8")
before = t3.read_bytes()
r = subprocess.run([PY, str(D / "clean.py"), str(t3), "--dry-run"], capture_output=True, text=True)
print(r.stdout)
assert t3.read_bytes() == before, "dry-run изменил файл!"
assert "примеры" in r.stdout, "превью не показано"
print("ТЕСТ 2 пройден: dry-run превью, файл не тронут")

# 3. restore
r = subprocess.run([PY, str(D / "clean.py"), str(t3), "--backup"], capture_output=True, text=True)
cleaned = t3.read_bytes()
assert cleaned != before, "чистка не сработала"
r = subprocess.run([PY, str(D / "clean.py"), str(t3), "--restore"], capture_output=True, text=True)
print(r.stdout)
assert t3.read_bytes() == before, "restore не вернул оригинал!"
print("ТЕСТ 3 пройден: restore вернул оригинал")

print("\nВСЕ ТЕСТЫ ПРОЙДЕНЫ")