# Ревью Помодоро — файл-накопитель (22.11, по просьбе владельца)

Владелец разбирает вкладку «Помодоро» с другой моделью (DeepSeek) и
будет накидывать сюда материал по частям: наблюдения, идеи, разборы,
цитаты из переписки. Задача этого файла — **только фиксировать**.

## Правила (договорились заранее)

1. **Код не пишем.** Пока идёт накопление — никаких правок вкладки,
   движков и тестов. Этот файл — единственное, что меняется.
2. Каждая порция от владельца попадает в «Журнал накопления» отдельной
   записью с датой: сначала источник (DeepSeek), потом суть, потом
   открытые вопросы — дословно насколько возможно, без пересказа.
3. Ничего не выбрасываем: даже спорное и отменённое остаётся в журнале
   с пометкой. Решения принимает владелец.
4. Когда накопление кончится, делаем разбор: сводка идей, плюсы/минусы,
   что ложится на текущую реализацию — и только потом, по решению
   владельца, план правок (тогда же здесь появится раздел «Итог разбора»).

## Журнал накопления

### Порция 1 — 22.11.2026, источник: DeepSeek (прислал владелец)

**Суть (слова владельца):** «Вот готовый промт и описание для агента,
который реализует метод Помодоро в режиме 50/10 (50 минут работы /
10 минут перерыва), адаптированный под рабочую деятельность».

Материал — два блока: промт для агента-ассистента и спецификация
этого агента. DeepSeek при этом предложил дополнительно (владелец
пока не выбирал): версию промта для Telegram-бота (кнопки
«Старт/Пауза/Стоп»), JSON-схему состояния, командную версию (общий
таймер).

#### 1.1. Промт для агента (дословно, копируется целиком)

```
Ты — персональный ассистент по управлению временем, работающий по методу Помодоро в режиме 50/10.

ТВОЯ ЗАДАЧА:
Помогать пользователю работать циклами: 50 минут сосредоточенной работы над одной задачей, затем 10 минут перерыва. После 4 циклов — длинный перерыв 30 минут.

ПРАВИЛА РАБОТЫ:
1. В начале сессии спроси пользователя:
   - Какую задачу он хочет выполнить?
   - Сколько циклов (помидоров) планирует потратить?
2. Перед каждым циклом напоминай: "Старт цикла N. 50 минут работы над задачей: [название]. Отключи уведомления."
3. Во время цикла не отвлекай пользователя. Если он пишет — отвечай кратко и напоминай вернуться к задаче.
4. Через 50 минут объяви: "Цикл N завершён. Перерыв 10 минут. Встань, разомнись, отвлекись от экрана."
5. Через 10 минут объяви: "Перерыв окончен. Готов к циклу N+1? Подтверди старт."
6. После 4-го цикла объяви длинный перерыв 30 минут.
7. В конце сессии подведи итог:
   - Сколько циклов выполнено
   - Какие задачи закрыты
   - Что отвлекало (если пользователь сообщал)
8. Веди журнал: фиксируй начало/конец каждого цикла, задачу, отвлечения.

ПОВЕДЕНИЕ ПРИ ОТВЛЕЧЕНИЯХ:
- Если пользователь сообщает об отвлечении — запиши его в журнал и предложи вернуться к задаче.
- Если цикл прерван более чем на 5 минут — предложи начать цикл заново.

СТИЛЬ ОБЩЕНИЯ:
- Кратко, чётко, поддерживающе.
- Не читай морали, не отвлекай лишними вопросами.
- Всегда указывай текущий статус: "Цикл 2/4 | Работа | Осталось 32 мин".

НАЧНИ С ПРИВЕТСТВИЯ И ВОПРОСА О ЗАДАЧЕ И ПЛАНЕ ЦИКЛОВ.
```

#### 1.2. Описание для агента (спецификация, дословно)

**Назначение.** Агент-таймер и трекер продуктивности для рабочих задач
по методу Помодоро с адаптированными интервалами 50/10 и длинным
перерывом 30 минут после 4 циклов.

**Целевая аудитория.** Сотрудники умственного труда: разработчики,
аналитики, дизайнеры, менеджеры — те, кому нужны длинные интервалы
глубокой работы.

**Функциональные требования:**

| Функция | Описание |
|---|---|
| Планирование сессии | Запрос задачи и количества циклов |
| Таймер цикла | 50 мин работы → 10 мин перерыва |
| Длинный перерыв | 30 мин после каждых 4 циклов |
| Статус-бар | Текущий цикл, фаза, оставшееся время |
| Журнал | Задачи, циклы, отвлечения, прерывания |
| Обработка отвлечений | Фиксация, мягкое возвращение к задаче |
| Итоговый отчёт | Кол-во циклов, закрытые задачи, паттерны отвлечений |

**Логика работы (state machine):**

```
IDLE → PLANNING → WORK(50) → SHORT_BREAK(10) → WORK(50) → ...
     → после 4-го WORK → LONG_BREAK(30) → PLANNING/IDLE
```

Состояния: IDLE — ожидание старта; PLANNING — сбор задачи и плана;
WORK — активный цикл (50 мин); SHORT_BREAK — короткий перерыв (10 мин);
LONG_BREAK — длинный перерыв (30 мин); PAUSED — пауза по запросу;
FINISHED — сессия завершена.

**Правила и ограничения:**

1. Одна задача на цикл — смена задачи только между циклами.
2. Прерывание цикла — если пауза >5 мин, цикл считается прерванным
   (предложить рестарт).
3. Не отвлекать во время WORK — только статус по запросу.
4. Перерывы обязательны — агент не начинает новый цикл без
   подтверждения перерыва.
5. Адаптивность — пользователь может изменить длительность (например,
   45/15), но по умолчанию 50/10.

**Формат статуса:**

```
[Цикл 2/4] Фаза: РАБОТА | Осталось: 32:15 | Задача: "Ревью PR #142"
```

**Формат итогового отчёта:**

```
Сессия завершена.
Циклов выполнено: 3 из 4
Задачи: 
  - Ревью PR #142 (2 цикла) — завершено
  - Написание документации (1 цикл) — в процессе
Отвлечения: 2 (почта, звонок)
Рекомендация: следующий раз отключить почту на время WORK-фаз.
```

**Интеграции (опционально):** календарь (блокировка слотов);
мессенджер (статус «не беспокоить»); трекер задач (Jira/Notion) —
привязка циклов к тикетам.

**Метрики эффективности:** кол-во завершённых циклов за день;
% циклов без прерываний; среднее время на задачу в «помидорах».

#### 1.3. Факты для сверки с текущей реализацией (без оценок)

* Материал описывает **отдельного ассистента-агента** (диалогового),
  а не вкладку GUI; связь с вкладкой «Помодоро» TextTools в порции
  не оговорена.
* Интервалы в материале: 50/10, длинный перерыв 30 мин после 4 циклов,
  адаптивность длительностей (пример 45/15).
* В материале заявлены: журнал циклов/отвлечений, итоговый отчёт
  сессии, метрики за день.

---

### Порция 2 — 22.11.2026, источник: DeepSeek (прислал владелец)

**Суть (слова владельца):** «Ниже — JSON-схема состояния (для
хранения/передачи), структура данных и готовая фича на Python в виде
модуля pomodoro.py, который можно встроить в приложение».

Материал — четыре блока: JSON-схема состояния, готовый Python-модуль
`pomodoro.py`, примеры встраивания (CLI / FastAPI / UI), список
«что важно помнить при интеграции». DeepSeek дополнительно предложил
(владелец пока не выбирал): SQLite-персистенцию (таблицы sessions,
journal), асинхронную версию (asyncio), Tkinter-виджет с прогресс-баром.

#### 2.1. JSON-схема состояния (дословно)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "PomodoroState",
  "type": "object",
  "required": ["session_id", "mode", "phase", "cycle", "cycles_planned", "task", "started_at", "phase_started_at", "phase_duration_sec", "paused", "journal"],
  "properties": {
    "session_id": { "type": "string", "format": "uuid" },
    "mode": { "type": "string", "enum": ["50/10", "25/5", "custom"] },
    "phase": { "type": "string", "enum": ["idle", "work", "short_break", "long_break", "paused", "finished"] },
    "cycle": { "type": "integer", "minimum": 0 },
    "cycles_planned": { "type": "integer", "minimum": 1 },
    "task": { "type": "string" },
    "started_at": { "type": "string", "format": "date-time" },
    "phase_started_at": { "type": "string", "format": "date-time" },
    "phase_duration_sec": { "type": "integer", "minimum": 0 },
    "paused": { "type": "boolean" },
    "paused_at": { "type": ["string", "null"], "format": "date-time" },
    "journal": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["ts", "event"],
        "properties": {
          "ts": { "type": "string", "format": "date-time" },
          "event": { "type": "string", "enum": ["start", "work_end", "break_start", "break_end", "pause", "resume", "interrupt", "finish", "note"] },
          "cycle": { "type": "integer" },
          "task": { "type": "string" },
          "meta": { "type": "object" }
        }
      }
    },
    "interruptions": { "type": "array", "items": { "type": "string" } },
    "settings": {
      "type": "object",
      "properties": {
        "work_sec": { "type": "integer", "default": 3000 },
        "short_break_sec": { "type": "integer", "default": 600 },
        "long_break_sec": { "type": "integer", "default": 1800 },
        "long_break_every": { "type": "integer", "default": 4 },
        "interrupt_threshold_sec": { "type": "integer", "default": 300 }
      }
    }
  }
}
```

**Пример заполненного состояния (дословно):**

```json
{
  "session_id": "3f2a9c1e-7b4d-4e21-9a55-1c2d3e4f5a6b",
  "mode": "50/10",
  "phase": "work",
  "cycle": 2,
  "cycles_planned": 4,
  "task": "Ревью PR #142",
  "started_at": "2026-11-20T09:00:00+03:00",
  "phase_started_at": "2026-11-20T10:00:00+03:00",
  "phase_duration_sec": 3000,
  "paused": false,
  "paused_at": null,
  "journal": [
    { "ts": "2026-11-20T09:00:00+03:00", "event": "start", "cycle": 1, "task": "Ревью PR #142" },
    { "ts": "2026-11-20T09:50:00+03:00", "event": "work_end", "cycle": 1 },
    { "ts": "2026-11-20T10:00:00+03:00", "event": "break_end", "cycle": 1 }
  ],
  "interruptions": ["почта", "звонок"],
  "settings": {
    "work_sec": 3000,
    "short_break_sec": 600,
    "long_break_sec": 1800,
    "long_break_every": 4,
    "interrupt_threshold_sec": 300
  }
}
```

#### 2.2. Python-модуль pomodoro.py (дословно, «готов к встраиванию»)

По словам DeepSeek: без внешних зависимостей (только stdlib);
логика — state machine; время считается через datetime, чтобы не
зависеть от частоты тиков; можно использовать с любым UI (Tkinter,
PyQt, FastAPI, CLI).

```python
"""
pomodoro.py — фича «Таймер-трекер Помодоро» (режим 50/10 и кастом).

Использование:
    from pomodoro import PomodoroTracker

    tracker = PomodoroTracker(work_sec=3000, short_break_sec=600,
                              long_break_sec=1800, long_break_every=4)
    tracker.start_session(task="Ревью PR #142", cycles_planned=4)

    # в цикле обновления UI (например, раз в секунду):
    status = tracker.tick()
    print(status.remaining_sec, status.phase)

    tracker.add_interruption("почта")
    tracker.pause(); tracker.resume()
    report = tracker.finish_session()
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ---------- ENUM ----------

class Phase(str, Enum):
    IDLE = "idle"
    WORK = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"
    PAUSED = "paused"
    FINISHED = "finished"


class Event(str, Enum):
    START = "start"
    WORK_END = "work_end"
    BREAK_START = "break_start"
    BREAK_END = "break_end"
    PAUSE = "pause"
    RESUME = "resume"
    INTERRUPT = "interrupt"
    FINISH = "finish"
    NOTE = "note"


# ---------- DATACLASSES ----------

def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)


@dataclass
class JournalEntry:
    ts: str
    event: Event
    cycle: int
    task: Optional[str] = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Status:
    phase: Phase
    cycle: int
    cycles_planned: int
    task: str
    remaining_sec: int
    total_sec: int
    paused: bool

    def bar(self) -> str:
        return (f"[Цикл {self.cycle}/{self.cycles_planned}] "
                f"Фаза: {self.phase.value.upper()} | "
                f"Осталось: {self.remaining_sec // 60:02d}:{self.remaining_sec % 60:02d} | "
                f"Задача: \"{self.task}\"")


# ---------- TRACKER ----------

class PomodoroTracker:
    def __init__(
        self,
        work_sec: int = 3000,
        short_break_sec: int = 600,
        long_break_sec: int = 1800,
        long_break_every: int = 4,
        interrupt_threshold_sec: int = 300,
    ) -> None:
        self.settings = {
            "work_sec": work_sec,
            "short_break_sec": short_break_sec,
            "long_break_sec": long_break_sec,
            "long_break_every": long_break_every,
            "interrupt_threshold_sec": interrupt_threshold_sec,
        }
        self.session_id: str = ""
        self.phase: Phase = Phase.IDLE
        self.cycle: int = 0
        self.cycles_planned: int = 0
        self.task: str = ""
        self.started_at: Optional[datetime] = None
        self.phase_started_at: Optional[datetime] = None
        self.phase_duration_sec: int = 0
        self.paused: bool = False
        self.paused_at: Optional[datetime] = None
        self.paused_accum_sec: int = 0  # накопленное время паузы в текущей фазе
        self.journal: list[JournalEntry] = []
        self.interruptions: list[str] = []

    # ---------- helpers ----------

    def _log(self, event: Event, task: Optional[str] = None, **meta) -> None:
        self.journal.append(JournalEntry(
            ts=now_iso(), event=event, cycle=self.cycle,
            task=task or (self.task if self.phase == Phase.WORK else None),
            meta=meta or {},
        ))

    def _enter_phase(self, phase: Phase, duration_sec: int) -> None:
        self.phase = phase
        self.phase_started_at = datetime.now(timezone.utc)
        self.phase_duration_sec = duration_sec
        self.paused = False
        self.paused_at = None
        self.paused_accum_sec = 0

    def _elapsed_sec(self) -> int:
        if self.phase_started_at is None:
            return 0
        if self.paused and self.paused_at is not None:
            end = self.paused_at
        else:
            end = datetime.now(timezone.utc)
        delta = (end - self.phase_started_at).total_seconds()
        return max(0, int(delta) - self.paused_accum_sec)

    # ---------- public API ----------

    def start_session(self, task: str, cycles_planned: int) -> Status:
        self.session_id = str(uuid.uuid4())
        self.cycles_planned = max(1, cycles_planned)
        self.task = task
        self.cycle = 1
        self.started_at = datetime.now(timezone.utc)
        self.journal.clear()
        self.interruptions.clear()
        self._enter_phase(Phase.WORK, self.settings["work_sec"])
        self._log(Event.START, task=task)
        return self.status()

    def start_next_cycle(self, task: Optional[str] = None) -> Status:
        """Ручной старт следующего рабочего цикла (после перерыва)."""
        if task:
            self.task = task
        self.cycle += 1
        self._enter_phase(Phase.WORK, self.settings["work_sec"])
        self._log(Event.START, task=self.task)
        return self.status()

    def tick(self) -> Status:
        """
        Вызывать регулярно (раз в секунду). Автоматически переключает фазы.
        """
        if self.phase in (Phase.IDLE, Phase.FINISHED, Phase.PAUSED):
            return self.status()

        elapsed = self._elapsed_sec()
        if elapsed < self.phase_duration_sec:
            return self.status()

        # фаза завершилась — переключаем
        if self.phase == Phase.WORK:
            self._log(Event.WORK_END)
            if self.cycle >= self.cycles_planned:
                self._finish()
            elif self.cycle % self.settings["long_break_every"] == 0:
                self._enter_phase(Phase.LONG_BREAK, self.settings["long_break_sec"])
                self._log(Event.BREAK_START, kind="long")
            else:
                self._enter_phase(Phase.SHORT_BREAK, self.settings["short_break_sec"])
                self._log(Event.BREAK_START, kind="short")
        elif self.phase in (Phase.SHORT_BREAK, Phase.LONG_BREAK):
            self._log(Event.BREAK_END)
            self._enter_phase(Phase.WORK, self.settings["work_sec"])
            self.cycle += 1
            self._log(Event.START, task=self.task)

        return self.status()

    def pause(self) -> Status:
        if self.phase in (Phase.WORK, Phase.SHORT_BREAK, Phase.LONG_BREAK) and not self.paused:
            self.paused = True
            self.paused_at = datetime.now(timezone.utc)
            self._log(Event.PAUSE)
        return self.status()

    def resume(self) -> Status:
        if self.paused and self.paused_at is not None:
            self.paused_accum_sec += int(
                (datetime.now(timezone.utc) - self.paused_at).total_seconds()
            )
            self.paused = False
            self.paused_at = None
            self._log(Event.RESUME)
            # если пауза была дольше порога — считаем цикл прерванным
            if self.paused_accum_sec >= self.settings["interrupt_threshold_sec"] and self.phase == Phase.WORK:
                self._log(Event.INTERRUPT, reason="pause_exceeded_threshold")
        return self.status()

    def add_interruption(self, reason: str) -> None:
        self.interruptions.append(reason)
        self._log(Event.INTERRUPT, reason=reason)

    def status(self) -> Status:
        remaining = max(0, self.phase_duration_sec - self._elapsed_sec())
        return Status(
            phase=self.phase,
            cycle=self.cycle,
            cycles_planned=self.cycles_planned,
            task=self.task,
            remaining_sec=remaining,
            total_sec=self.phase_duration_sec,
            paused=self.paused,
        )

    def finish_session(self) -> dict[str, Any]:
        if self.phase != Phase.FINISHED:
            self._finish()
        return self.report()

    def _finish(self) -> None:
        self._log(Event.FINISH)
        self.phase = Phase.FINISHED

    def report(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "cycles_planned": self.cycles_planned,
            "cycles_completed": max(0, self.cycle - (0 if self.phase == Phase.FINISHED else 1)),
            "task": self.task,
            "interruptions": self.interruptions,
            "journal": [asdict(j) for j in self.journal],
        }

    # ---------- сериализация ----------

    def to_json(self) -> str:
        return json.dumps({
            "session_id": self.session_id,
            "mode": f"{self.settings['work_sec']//60}/{self.settings['short_break_sec']//60}",
            "phase": self.phase.value,
            "cycle": self.cycle,
            "cycles_planned": self.cycles_planned,
            "task": self.task,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "phase_started_at": self.phase_started_at.isoformat() if self.phase_started_at else None,
            "phase_duration_sec": self.phase_duration_sec,
            "paused": self.paused,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "journal": [asdict(j) for j in self.journal],
            "interruptions": self.interruptions,
            "settings": self.settings,
        }, ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, data: str | dict) -> "PomodoroTracker":
        if isinstance(data, str):
            data = json.loads(data)
        s = data.get("settings", {})
        t = cls(
            work_sec=s.get("work_sec", 3000),
            short_break_sec=s.get("short_break_sec", 600),
            long_break_sec=s.get("long_break_sec", 1800),
            long_break_every=s.get("long_break_every", 4),
            interrupt_threshold_sec=s.get("interrupt_threshold_sec", 300),
        )
        t.session_id = data.get("session_id", "")
        t.phase = Phase(data.get("phase", "idle"))
        t.cycle = data.get("cycle", 0)
        t.cycles_planned = data.get("cycles_planned", 0)
        t.task = data.get("task", "")
        t.started_at = parse_iso(data["started_at"]) if data.get("started_at") else None
        t.phase_started_at = parse_iso(data["phase_started_at"]) if data.get("phase_started_at") else None
        t.phase_duration_sec = data.get("phase_duration_sec", 0)
        t.paused = data.get("paused", False)
        t.paused_at = parse_iso(data["paused_at"]) if data.get("paused_at") else None
        t.interruptions = data.get("interruptions", [])
        t.journal = [
            JournalEntry(
                ts=j["ts"],
                event=Event(j["event"]),
                cycle=j.get("cycle", 0),
                task=j.get("task"),
                meta=j.get("meta", {}),
            )
            for j in data.get("journal", [])
        ]
        return t
```

#### 2.3. Как встроить в приложение (примеры DeepSeek, дословно)

**CLI-цикл:**

```python
import time
from pomodoro import PomodoroTracker

t = PomodoroTracker()  # 50/10 по умолчанию
t.start_session(task="Ревью PR #142", cycles_planned=4)

while True:
    st = t.tick()
    print("\r" + st.bar(), end="", flush=True)
    if st.phase.value == "finished":
        break
    time.sleep(1)

print("\n\nИтог:")
print(t.to_json())
```

**FastAPI-эндпоинты (кратко):**

```python
from fastapi import FastAPI
from pomodoro import PomodoroTracker

app = FastAPI()
trackers: dict[str, PomodoroTracker] = {}

@app.post("/session")
def create(task: str, cycles: int):
    t = PomodoroTracker()
    t.start_session(task, cycles)
    trackers[t.session_id] = t
    return {"session_id": t.session_id}

@app.get("/session/{sid}")
def status(sid: str):
    t = trackers[sid]
    t.tick()  # обновить фазу
    return t.status().__dict__

@app.post("/session/{sid}/pause")
def pause(sid: str):
    return trackers[sid].pause().__dict__

@app.post("/session/{sid}/interrupt")
def interrupt(sid: str, reason: str):
    trackers[sid].add_interruption(reason)
    return {"ok": True}

@app.get("/session/{sid}/report")
def report(sid: str):
    return trackers[sid].report()
```

**В UI (Tkinter/PyQt):** запускать `tick()` через QTimer/`after(1000, ...)`;
для статус-бара брать `status().bar()` или поля `remaining_sec` / `phase`;
для сохранения сессии — `to_json()` в файл/БД, для восстановления —
`PomodoroTracker.from_json(...)`.

#### 2.4. «Что важно помнить при интеграции» (дословный список DeepSeek)

* Не блокируй поток — `tick()` должен вызываться извне (UI-loop или
  отдельный поток с threading.Event).
* Время — через datetime, а не счётчик тиков: устойчиво к пропущенным
  тикам и сну системы.
* Пауза учитывается через `paused_accum_sec` — не сбивает фазу.
* Длинный перерыв включается автоматически после long_break_every-го
  цикла (по умолчанию 4).
* Прерывание фиксируется, если пауза в WORK превысила
  interrupt_threshold_sec (300 с = 5 мин), как в описании агента.
* `report()` даёт готовый блок для итогового экрана/лога.

#### 2.5. Факты для сверки (без оценок)

* Модуль — **самодостаточная реализация** (enum Phase/Event, journal,
  сериализация to_json/from_json, порог прерывания 300 с) — это уже
  не только «схема», но и логика; как она соотносится с текущим кодом
  вкладки «Помодоро» TextTools, в порции не разбирается.
* Настройки модуля: 50 мин / 10 мин / 30 мин (long), long_break_every=4,
  interrupt_threshold_sec=300 — совпадают с параметрами порции 1.
* События журнала: start, work_end, break_start, break_end, pause,
  resume, interrupt, finish, note.
* DeepSeek предлагает дополнительное (не выбрано): SQLite-персистенция,
  asyncio-версия, Tkinter-виджет.

## Открытые вопросы

1. Порция 1: материал — про отдельного агента-ассистента. Что берём
   для вкладки «Помодоро» TextTools (идеи/правила целиком или частями),
   а что остаётся за рамками проекта — решит владелец при разборе.
2. Порция 1: DeepSeek предложил три дополнения (Telegram-бот,
   JSON-схема, командный таймер) — брать или нет, не выбрано.
3. Порция 2: pomodoro.py — уже готовая реализация, а не только схема.
   Не решено: встраивать как есть, вливать в текущий код вкладки
   «Помодоро» или держать как референс.

## Итог разбора

*(не начат — заполняется после согласования с владельцем)*
