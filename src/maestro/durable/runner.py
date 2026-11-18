"""مُشغّل متين: مهمة تُنفَّذ مرّة واحدة مهما تكرّر الطلب.

الفكرة: قبل التنفيذ نكتب «بدأت»، وبعده نكتب «انتهت». إن ماتت العملية بين
الكتابةين، تُستأنف المهمة من السجل. وإن وصل الطلب بمفتاح تكرارية نفسه بعد
الإنجاز، نعيد النتيجة المخزّنة ولا نُنفّذ ولا نُنفق.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..runtime.runner import CapabilityRunner, ExecutionReport
from .journal import DurableJournal


@dataclass(frozen=True)
class DurableOutcome:
    """نتيجة تنفيذ متين."""

    task_id: str
    status: str  # done | cached | failed
    report: ExecutionReport
    idempotency_key: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "idempotency_key": self.idempotency_key,
            "report": self.report.as_dict(),
        }


class DurableRunner:
    """غلاف متين حول مُشغّل القدرة."""

    def __init__(self, capability_runner: CapabilityRunner, journal: DurableJournal):
        self.capability_runner = capability_runner
        self.journal = journal

    def execute(
        self,
        task_id: str,
        doc: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> DurableOutcome:
        """ينفّذ المهمة، أو يعيد النتيجة المخزّنة إن سبق إنجازها."""
        capability = str(doc.get("capability", ""))
        key = idempotency_key or f"{task_id}:{capability}"

        cached = self.journal.completed(key)
        if cached is not None:
            report = ExecutionReport(
                capability=capability,
                ok=True,
                stage="cached",
                detail_ar="النتيجة محفوظة: أُعيدت دون تنفيذ جديد.",
                output=cached.payload.get("output"),
                evidence_hash=cached.payload.get("evidence_hash"),
            )
            return DurableOutcome(
                task_id=task_id,
                status="cached",
                report=report,
                idempotency_key=key,
            )

        self.journal.append(
            task_id=task_id,
            event="started",
            idempotency_key=key,
            capability=capability,
            payload={"doc": doc},
        )
        report = self.capability_runner.run(doc)
        if report.ok:
            self.journal.append(
                task_id=task_id,
                event="finished",
                idempotency_key=key,
                capability=capability,
                payload={
                    "output": report.output,
                    "evidence_hash": report.evidence_hash,
                    "stage": report.stage,
                },
            )
            status = "done"
        else:
            self.journal.append(
                task_id=task_id,
                event="failed",
                idempotency_key=key,
                capability=capability,
                payload={"stage": report.stage, "detail_ar": report.detail_ar},
            )
            status = "failed"

        return DurableOutcome(
            task_id=task_id,
            status=status,
            report=report,
            idempotency_key=key,
        )

    def resume_pending(self) -> list[DurableOutcome]:
        """يستأنف كل مهمة بدأت ولم تنتهِ."""
        outcomes: list[DurableOutcome] = []
        for record in self.journal.pending():
            doc = record.payload.get("doc")
            if not isinstance(doc, dict):
                continue
            outcomes.append(
                self.execute(
                    record.task_id,
                    doc,
                    idempotency_key=record.idempotency_key,
                )
            )
        return outcomes
