"""سجل المتانة: سجل إلحاقي لحالات المهام.

لماذا سجل خطّي بسيط بدل قاعدة بيانات: النواة يجب أن تعمل بلا خدمة
خارجية وبلا تكلفة. الاستئناف لا يحتاج أكثر من سجل يُقرأ من بدايته.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: أحداث نهاية المهمة.
TERMINAL_EVENTS: frozenset[str] = frozenset({"finished", "failed", "rejected"})


@dataclass(frozen=True)
class JournalRecord:
    """سطر واحد في سجل المتانة."""

    seq: int
    task_id: str
    event: str
    idempotency_key: str
    capability: str
    payload: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "task_id": self.task_id,
            "event": self.event,
            "idempotency_key": self.idempotency_key,
            "capability": self.capability,
            "payload": self.payload,
        }


class DurableJournal:
    """سجل JSONL لحالات المهام."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def append(
        self,
        *,
        task_id: str,
        event: str,
        idempotency_key: str,
        capability: str,
        payload: dict[str, Any] | None = None,
    ) -> JournalRecord:
        """يضيف سطراً جديداً ويعيده."""
        records = self.records()
        record = JournalRecord(
            seq=len(records) + 1,
            task_id=task_id,
            event=event,
            idempotency_key=idempotency_key,
            capability=capability,
            payload=payload or {},
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        return record

    def records(self) -> list[JournalRecord]:
        """كل أسطر السجل بالترتيب."""
        if not self.path.exists():
            return []
        records: list[JournalRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            records.append(
                JournalRecord(
                    seq=raw["seq"],
                    task_id=raw["task_id"],
                    event=raw["event"],
                    idempotency_key=raw["idempotency_key"],
                    capability=raw["capability"],
                    payload=raw["payload"],
                )
            )
        return records

    def completed(self, idempotency_key: str) -> JournalRecord | None:
        """سطر الإنجاز إن وُجد لهذا المفتاح."""
        for record in reversed(self.records()):
            if record.idempotency_key == idempotency_key and record.event == "finished":
                return record
        return None

    def pending(self) -> list[JournalRecord]:
        """مهام بدأت ولم تنتهِ — مرشّحة للاستئناف."""
        started: dict[str, JournalRecord] = {}
        finished: set[str] = set()
        for record in self.records():
            if record.event == "started":
                started[record.task_id] = record
            elif record.event in TERMINAL_EVENTS:
                finished.add(record.task_id)
        return [record for task_id, record in started.items() if task_id not in finished]
