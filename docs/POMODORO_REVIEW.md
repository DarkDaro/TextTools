# Ревью Помодоро — файл-накопитель (22.11, по просьбе владельца)

> **Статус 22.11.2026: накопление ЗАВЕРШЕНО владельцем (порция 5).**
> Разбор («Итог разбора») ещё не начат — стартует по команде владельца.

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

---

### Порция 3 — 22.11.2026, источник: DeepSeek (прислал владелец)

**Суть (слова владельца):** «Ниже — готовый Tkinter-виджет
PomodoroWidget, который встраивается в любое окно (pack/grid/place),
использует уже написанный PomodoroTracker и даёт: прогресс-бар,
статус, кнопки Старт/Пауза/Продолжить/Стоп, поле задачи, счётчик
циклов, кнопку „Отвлечение" и итоговый отчёт».

Материал — три блока: `pomodoro_widget.py`, демо-запуск `demo.py`,
список «что важно знать». DeepSeek перечислил возможные расширения
(не выбрано): SQLite-персистенция (sessions, journal, interruptions),
трей-иконка (pystray), звук/уведомление на смену фазы, вкладка
настроек длительностей, экспорт отчёта в CSV/JSON; следующий шаг —
SQLite + вкладка настроек, по словам DeepSeek «если нужно».

#### 3.1. Файл pomodoro_widget.py (дословно)

```python
"""
pomodoro_widget.py — Tkinter-виджет таймера-трекера Помодоро (50/10).

Требует pomodoro.py (PomodoroTracker) в том же пакете/папке.

Использование:
    import tkinter as tk
    from pomodoro_widget import PomodoroWidget

    root = tk.Tk()
    w = PomodoroWidget(root)
    w.pack(fill="both", expand=True)
    root.mainloop()
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from pomodoro import PomodoroTracker, Phase


class PomodoroWidget(ttk.Frame):
    """Виджет Помодоро: таймер, прогресс, журнал, отчёт."""

    TICK_MS = 500  # частота обновления UI (0.5 c — плавно и не грузит CPU)

    def __init__(self, master, tracker: Optional[PomodoroTracker] = None, **kw):
        super().__init__(master, padding=12, **kw)
        self.tracker = tracker or PomodoroTracker()  # 50/10 по умолчанию
        self._after_id: Optional[str] = None
        self._build_ui()
        self._set_controls_state(running=False)

    # ---------- UI ----------

    def _build_ui(self) -> None:
        # --- Верхняя панель: задача и план ---
        top = ttk.LabelFrame(self, text="Сессия", padding=8)
        top.pack(fill="x", pady=(0, 8))

        ttk.Label(top, text="Задача:").grid(row=0, column=0, sticky="w")
        self.task_var = tk.StringVar(value="Ревью PR #142")
        ttk.Entry(top, textvariable=self.task_var, width=40).grid(
            row=0, column=1, sticky="we", padx=(6, 12)
        )

        ttk.Label(top, text="Циклов:").grid(row=0, column=2, sticky="w")
        self.cycles_var = tk.IntVar(value=4)
        ttk.Spinbox(top, from_=1, to=12, textvariable=self.cycles_var, width=4).grid(
            row=0, column=3, sticky="w", padx=(6, 0)
        )
        top.columnconfigure(1, weight=1)

        # --- Статус ---
        status = ttk.LabelFrame(self, text="Статус", padding=8)
        status.pack(fill="x", pady=(0, 8))

        self.phase_var = tk.StringVar(value="IDLE")
        self.cycle_var = tk.StringVar(value="—")
        self.time_var = tk.StringVar(value="00:00")

        ttk.Label(status, textvariable=self.phase_var,
                  font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(status, textvariable=self.cycle_var,
                  font=("Segoe UI", 11)).grid(row=0, column=1, sticky="e", padx=(12, 0))
        ttk.Label(status, textvariable=self.time_var,
                  font=("Consolas", 22, "bold")).grid(row=1, column=0, columnspan=2, pady=(4, 6))
        status.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(status, orient="horizontal", mode="determinate", maximum=100)
        self.progress.grid(row=2, column=0, columnspan=2, sticky="we")

        # --- Кнопки ---
        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=(0, 8))

        self.btn_start = ttk.Button(btns, text="▶ Старт", command=self.on_start)
        self.btn_pause = ttk.Button(btns, text="⏸ Пауза", command=self.on_pause)
        self.btn_resume = ttk.Button(btns, text="⏵ Продолжить", command=self.on_resume)
        self.btn_stop = ttk.Button(btns, text="■ Стоп", command=self.on_stop)
        self.btn_interrupt = ttk.Button(btns, text="⚠ Отвлечение", command=self.on_interrupt)

        for b in (self.btn_start, self.btn_pause, self.btn_resume, self.btn_stop, self.btn_interrupt):
            b.pack(side="left", padx=(0, 6))

        # --- Журнал ---
        log = ttk.LabelFrame(self, text="Журнал", padding=8)
        log.pack(fill="both", expand=True)
        self.log_text = tk.Text(log, height=10, wrap="word", state="disabled",
                                font=("Consolas", 9))
        scroll = ttk.Scrollbar(log, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # ---------- helpers ----------

    def _set_controls_state(self, running: bool, paused: bool = False) -> None:
        self.btn_start.state(["!disabled"] if not running else ["disabled"])
        self.btn_pause.state(["!disabled"] if (running and not paused) else ["disabled"])
        self.btn_resume.state(["!disabled"] if (running and paused) else ["disabled"])
        self.btn_stop.state(["!disabled"] if running else ["disabled"])
        self.btn_interrupt.state(["!disabled"] if running else ["disabled"])

    def _log(self, msg: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _schedule_tick(self) -> None:
        if self._after_id is not None:
            self.after_cancel(self._after_id)
        self._after_id = self.after(self.TICK_MS, self._tick)

    # ---------- UI update ----------

    def _update_ui(self) -> None:
        st = self.tracker.status()
        phase_label = {
            Phase.IDLE: "ГОТОВ",
            Phase.WORK: "РАБОТА",
            Phase.SHORT_BREAK: "ПЕРЕРЫВ (короткий)",
            Phase.LONG_BREAK: "ПЕРЕРЫВ (длинный)",
            Phase.PAUSED: "ПАУЗА",
            Phase.FINISHED: "ЗАВЕРШЕНО",
        }.get(st.phase, st.phase.value)

        if st.paused:
            phase_label = "ПАУЗА"

        self.phase_var.set(phase_label)
        self.cycle_var.set(f"Цикл {st.cycle}/{st.cycles_planned}" if st.cycles_planned else "—")
        m, s = divmod(st.remaining_sec, 60)
        self.time_var.set(f"{m:02d}:{s:02d}")

        if st.total_sec > 0:
            done = (st.total_sec - st.remaining_sec) / st.total_sec * 100
            self.progress["value"] = max(0.0, min(100.0, done))
        else:
            self.progress["value"] = 0

    # ---------- events ----------

    def on_start(self) -> None:
        task = self.task_var.get().strip()
        if not task:
            messagebox.showwarning("Помодоро", "Укажи задачу.")
            return
        cycles = max(1, self.cycles_var.get())
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        self.tracker.start_session(task=task, cycles_planned=cycles)
        self._log(f"▶ Старт сессии: «{task}», план {cycles} цикл(ов).")
        self._set_controls_state(running=True, paused=False)
        self._update_ui()
        self._schedule_tick()

    def on_pause(self) -> None:
        self.tracker.pause()
        self._log("⏸ Пауза.")
        self._set_controls_state(running=True, paused=True)
        self._update_ui()

    def on_resume(self) -> None:
        self.tracker.resume()
        self._log("⏵ Продолжение.")
        self._set_controls_state(running=True, paused=False)
        self._update_ui()

    def on_stop(self) -> None:
        if not messagebox.askyesno("Помодоро", "Завершить сессию?"):
            return
        report = self.tracker.finish_session()
        self._show_report(report)
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._set_controls_state(running=False)
        self._update_ui()

    def on_interrupt(self) -> None:
        dlg = tk.Toplevel(self)
        dlg.title("Отвлечение")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        ttk.Label(dlg, text="Что отвлекло?").pack(padx=10, pady=(10, 4))
        var = tk.StringVar()
        entry = ttk.Entry(dlg, textvariable=var, width=40)
        entry.pack(padx=10)
        entry.focus_set()

        def ok():
            reason = var.get().strip() or "без причины"
            self.tracker.add_interruption(reason)
            self._log(f"⚠ Отвлечение: {reason}")
            dlg.destroy()

        ttk.Button(dlg, text="OK", command=ok).pack(pady=8)
        dlg.bind("<Return>", lambda e: ok())
        dlg.wait_visibility()
        self.wait_window(dlg)

    # ---------- tick-loop ----------

    def _tick(self) -> None:
        prev_phase = self.tracker.phase
        st = self.tracker.tick()
        self._update_ui()

        # логируем автопереходы фаз
        if st.phase != prev_phase:
            if st.phase == Phase.SHORT_BREAK:
                self._log("☕ Короткий перерыв 10 мин.")
            elif st.phase == Phase.LONG_BREAK:
                self._log("🛋 Длинный перерыв 30 мин.")
            elif st.phase == Phase.WORK:
                self._log(f"▶ Цикл {st.cycle} — работа 50 мин.")
            elif st.phase == Phase.FINISHED:
                self._log("✅ Сессия завершена.")
                self._show_report(self.tracker.report())
                self._set_controls_state(running=False)
                self._after_id = None
                return

        if st.phase in (Phase.IDLE, Phase.FINISHED):
            self._after_id = None
            return

        self._schedule_tick()

    # ---------- report ----------

    def _show_report(self, report: dict) -> None:
        dlg = tk.Toplevel(self)
        dlg.title("Итог сессии")
        dlg.transient(self.winfo_toplevel())
        text = tk.Text(dlg, width=60, height=18, wrap="word", font=("Consolas", 9))
        text.pack(fill="both", expand=True, padx=10, pady=10)

        lines = [
            f"Задача: {report.get('task', '')}",
            f"Циклов выполнено: {report.get('cycles_completed', 0)} / {report.get('cycles_planned', 0)}",
            f"Отвлечения: {', '.join(report.get('interruptions', [])) or '—'}",
            "",
            "Журнал:",
        ]
        for j in report.get("journal", []):
            lines.append(f"  {j['ts']}  [{j['event']}]  cycle={j.get('cycle', '')}")
        text.insert("1.0", "\n".join(lines))
        text.configure(state="disabled")
        ttk.Button(dlg, text="Закрыть", command=dlg.destroy).pack(pady=(0, 10))
```

#### 3.2. Демо-запуск demo.py (дословно)

```python
import tkinter as tk
from tkinter import ttk
from pomodoro_widget import PomodoroWidget

def main():
    root = tk.Tk()
    root.title("Помодоро 50/10 — демо")
    root.geometry("560x640")

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    w = PomodoroWidget(root)
    w.pack(fill="both", expand=True)
    root.mainloop()

if __name__ == "__main__":
    main()
```

По словам DeepSeek: положить `pomodoro.py` и `pomodoro_widget.py`
рядом, затем `python demo.py`.

#### 3.3. «Что важно знать» (дословный список DeepSeek)

* Автопереходы фаз обрабатываются в `_tick()` через `tracker.tick()` —
  виджет только рисует.
* Пауза останавливает datetime-таймер внутри трекера; UI просто
  перерисовывает статус.
* Отвлечение логируется в `tracker.interruptions` и в журнал; порог
  5 мин на паузу — в трекере (при resume после долгой паузы в WORK
  пишется interrupt).
* Отчёт показывается и при ручном стопе, и при автозавершении после
  последнего цикла.
* Тик 500 мс — компромисс: плавно и без нагрузки; можно поменять
  `TICK_MS`.
* Персистенция не встроена: если нужна — сохранять `tracker.to_json()`
  в файл/БД на `on_stop` и на закрытии окна, восстанавливать через
  `PomodoroTracker.from_json` и передавать в
  `PomodoroWidget(tracker=...)`.

#### 3.4. Возможные расширения (перечислены DeepSeek, «если захотите»)

1. Сохранение в SQLite — таблицы sessions, journal, interruptions.
2. Трей-иконка (pystray) с обратным отсчётом в заголовке.
3. Звук/уведомление на смену фазы (winsound / playsound / notifypy).
4. Настройки длительности в отдельной вкладке (ttk.Notebook) —
   «уже поддерживается PomodoroTracker(work_sec=...)».
5. Экспорт отчёта в CSV/JSON через `tracker.to_json()`.

#### 3.5. Факты для сверки (без оценок)

* Виджет — **готовая UI-реализация на Tkinter/ttk** поверх трекера из
  порции 2 (импортирует `from pomodoro import PomodoroTracker, Phase`);
  связь с GUI TextTools (customtkinter, вкладка «Помодоро») в порции
  не разбирается.
* UI-элементы: поле задачи + Spinbox циклов (1–12), фаза/цикл/таймер,
  прогресс-бар, 5 кнопок (Старт/Пауза/Продолжить/Стоп/Отвлечение),
  журнал (Text+Scrollbar), модальные диалоги отвлечения и итогового
  отчёта.
* Тик UI — 500 мс через `after()` (в порции 2 рекомендовалось 1000 мс);
  логика времени по-прежнему в трекере на datetime.
* Расширения DeepSeek нарастают (SQLite, трей, звук, вкладка
  настроек, CSV/JSON-экспорт) — ни одно не выбрано.

---

### Порция 4 — 22.11.2026, источник: DeepSeek (прислал владелец) — **НЕПОЛНАЯ**

**Суть (слова владельца, дословно):** «Ниже — расширенная версия:
pomodoro.py (с SQLite-персистенцией), pomodoro_widget.py (с вкладкой
„Настройки" и сохранением/восстановлением сессии) и demo.py. Всё
по-прежнему без внешних зависимостей — только stdlib».

**Внимание:** до файла дошло только это вводное предложение. Самих
материалов — кода `pomodoro.py` (SQLite), `pomodoro_widget.py`
(вкладка «Настройки», сохранение/восстановление) и `demo.py` — в
сообщении не было (вероятно, обрезалось при отправке). Запись
намеренно оставлена неполной, чтобы не пересказывать код по памяти и
не искажать дословность. Ожидается повторная отправка тела порции;
после неё эта порция будет дополнена дословным текстом.

#### 4.1. Факты для сверки (без оценок, по вводной фразе)

* Расширенная версия развивает порции 2–3: SQLite-персистенция
  (обещана ещё в порциях 2–3 как опция) и вкладка настроек с
  сохранением/восстановлением сессии (тоже числилась в расширениях).
* Заявлено отсутствие внешних зависимостей — «только stdlib» (для
  SQLite это согласуется с модулем sqlite3 из стандартной библиотеки).

#### 4.2. Сопроводительное сообщение DeepSeek (дословно, пришло вторым сообщением; тела кода по-прежнему нет)

```
Отлично! 👍 У вас на руках всё необходимое:

· pomodoro.py — трекер + SQLite (sessions, journal, interruptions, settings).
· pomodoro_widget.py — Tkinter-виджет с вкладками «Таймер» и «Настройки», журналом, историей и отчётом.
· demo.py — точка входа.

Пара мелочей на память для агента:

1. Порядок файлов — pomodoro.py и pomodoro_widget.py в одной папке (или в пакете с __init__.py).
2. pomodoro.db создаётся автоматически рядом с запуском — путь можно поменять через PomodoroWidget(..., db_path=...).
3. Настройки из вкладки применяются к следующей сессии (трекер пересоздаётся в on_start) — это осознанное решение, чтобы не сбивать текущий цикл.
4. Тик 500 мс — если агенту понадобится плавнее/экономнее, менять TICK_MS.
5. Расширения (автосейв состояния, экспорт CSV, статистика, трей, звук) — схема БД и API уже под них заточены.

Если в процессе интеграции у агента возникнут вопросы по поведению (например, «что делать с незавершённой сессией при закрытии окна» или «как считать cycles_completed при ручном стопе») — возвращайтесь, разберём точечно. Удачи с фичей! 🍅
```

#### 4.3. Факты для сверки из сопроводительного сообщения (без оценок)

* Состав расширенной версии (по описанию DeepSeek): `pomodoro.py` —
  трекер + SQLite (таблицы sessions, journal, interruptions, settings);
  `pomodoro_widget.py` — Tkinter-виджет с вкладками «Таймер» и
  «Настройки», журналом, историей и отчётом; `demo.py` — точка входа.
* Поведенческие решения, заявленные DeepSeek: `pomodoro.db`
  создаётся автоматически рядом с запуском, путь переопределяется
  через `PomodoroWidget(..., db_path=...)`; настройки из вкладки
  применяются к **следующей** сессии (трекер пересоздаётся в
  `on_start`) — «осознанное решение, чтобы не сбивать текущий цикл»;
  тик 500 мс настраивается через `TICK_MS`.
* Заявлена готовность схемы БД и API под расширения: автосейв
  состояния, экспорт CSV, статистика, трей, звук.
* DeepSeek сам назвал открытые поведенческие вопросы интеграции:
  «что делать с незавершённой сессией при закрытии окна» и «как
  считать cycles_completed при ручном стопе» — предложить вернуться
  и разобрать точечно.
* Тела файлов (полный код) в обоих сообщениях порции 4 не дошли —
  порция остаётся неполной: есть описания и поведенческие решения,
  нет дословного кода.

---

### Порция 5 — 22.11.2026, владелец — **закрытие обсуждения**

Слова владельца (дословно): «Да это конец обсуждения. код выше.
Я не настолько нужен SQLite, sql я не знаю. также нужно да сделать
режим еще 50/10».

**Решения владельца при закрытии накопления:**

1. Обсуждение с DeepSeek окончено — накопление материала завершено.
2. **SQLite не нужен** — владелец SQL не знает; SQLite-персистенция
   из порций 2–4 отпадает. (Сериализация to_json/from_json из
   порции 2 при этом не отозвана.)
3. **Режим 50/10 нужен** — владелец явно подтвердил («нужно да
   сделать режим еще 50/10»); это режим по умолчанию во всех
   порциях DeepSeek (трекер порции 2: work_sec=3000,
   short_break_sec=600).
4. Тела файлов порции 4 владельцем повторно не присылались
   («код выше»); порция 4 остаётся неполной — есть вводная фраза и
   сопроводительное сообщение, нет дословного кода.

## Открытые вопросы

1. Порция 1: материал — про отдельного агента-ассистента. Что берём
   для вкладки «Помодоро» TextTools (идеи/правила целиком или частями),
   а что остаётся за рамками проекта — решит владелец при разборе.
2. Порция 1: дополнения DeepSeek — Telegram-бот и командный таймер
   не выбраны; JSON-схема пришла в порции 2. ~~SQLite~~ — **решено
   (порция 5): не нужен**. Режим 50/10 — **решено (порция 5): нужен**.
3. Порция 2: pomodoro.py — уже готовая реализация, а не только схема.
   Не решено: встраивать как есть, вливать в текущий код вкладки
   «Помодоро» или держать как референс.
4. Порция 3: pomodoro_widget.py — готовый Tkinter/ttk-виджет поверх
   трекера из порции 2. Не решено: переносить ли его элементы в
   вкладку «Помодоро» TextTools (GUI на customtkinter), брать как
   есть или держать как референс. Пять расширений DeepSeek (SQLite,
   трей, звук, вкладка настроек, экспорт) — ни одно не выбрано.
5. Тик UI: в порции 2 рекомендовано after(1000), в порции 3 виджет
   использует TICK_MS=500 — какой интервал брать, не решено.
6. Порция 4: тело порции (код расширенных pomodoro.py /
   pomodoro_widget.py / demo.py) не дошло — записана вводная фраза и
   сопроводительное сообщение DeepSeek (состав, db_path, настройки
   со следующей сессии, TICK_MS). Полного кода по-прежнему нет —
   вопрос о повторной отправке открыт.
7. Поведенческие вопросы, названные самим DeepSeek (порция 4):
   поведение при закрытии окна с незавершённой сессией; подсчёт
   cycles_completed при ручном стопе — разбрать при интеграции.

## Итог разбора

*(не начат — заполняется после согласования с владельцем)*
