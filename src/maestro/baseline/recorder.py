"""مسجّل الخط الأساسي: ما كان يعمله الإنسان قبل أن يتدخّل الوكيل.

ملاحظة مهمّة: هذه **قياسات** لا **بوابات**. لا يقبل المشروع بناءً على
«نسبة قبول 80%»؛ القبول هنا وصفٌ لقرار بشري، بينما بوابة الجودة
في هذا المستودع إمّا تجتاز وإمّا تفشل.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class BaselineRecord:
    """سطر خط أساسي واحد."""

    capability: str
    output_id: str
    human_minutes: float
    cost_usd: float
    accepted_unedited: bool
    repeat_within_2_weeks: bool | None
    timestamp: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaselineRecorder:
    """يكتب سطور الخط الأساسي في JSONL ويحسب تجميعات وصفية."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def record(
        self,
        *,
        capability: str,
        output_id: str,
        human_minutes: float,
        cost_usd: float,
        accepted_unedited: bool,
        repeat_within_2_weeks: bool | None = None,
        timestamp: str,
    ) -> BaselineRecord:
        """يسجّل سطراً واحداً ويعيده."""
        record = BaselineRecord(
            capability=capability,
            output_id=output_id,
            human_minutes=float(human_minutes),
            cost_usd=float(cost_usd),
            accepted_unedited=bool(accepted_unedited),
            repeat_within_2_weeks=repeat_within_2_weeks,
            timestamp=timestamp,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        return record

    def records(self, capability: str | None = None) -> list[BaselineRecord]:
        """كل السطور، أو سطور قدرة واحدة."""
        if not self.path.exists():
            return []
        records: list[BaselineRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            records.append(BaselineRecord(**raw))
        if capability is None:
            return records
        return [record for record in records if record.capability == capability]

    def summary(self, capability: str | None = None) -> dict[str, Any]:
        """تجميع وصفي: عدد المخرجات، الزمن البشري، التكلفة، القبول."""
        records = self.records(capability)
        if not records:
            return {
                "capability": capability,
                "outputs": 0,
                "mean_human_minutes": None,
                "mean_cost_usd": None,
                "accepted_unedited": None,
                "repeat_within_2_weeks": None,
            }
        count = len(records)
        repeats = [r.repeat_within_2_weeks for r in records if r.repeat_within_2_weeks is not None]
        return {
            "capability": capability,
            "outputs": count,
            "mean_human_minutes": sum(r.human_minutes for r in records) / count,
            "mean_cost_usd": sum(r.cost_usd for r in records) / count,
            "accepted_unedited": sum(1 for r in records if r.accepted_unedited) / count,
            "repeat_within_2_weeks": (sum(1 for r in repeats if r) / len(repeats)) if repeats else None,
        }
