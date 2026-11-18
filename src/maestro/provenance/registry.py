"""سجل التبعيات: كل حزمة تدخل المستودع لها قرار مكتوب ورخصة وتبرير."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Dependency:
    """قرار مسجَّل عن تبعية واحدة."""

    name: str
    license: str
    source: str
    decision: str  # allow | deny
    rationale_ar: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "license": self.license,
            "source": self.source,
            "decision": self.decision,
            "rationale_ar": self.rationale_ar,
        }


class ProvenanceRegistry:
    """قائمة التبعيات المسموحة والمرفوضة، مقروءة من JSON."""

    def __init__(self, entries: Iterable[Dependency]):
        self._entries: dict[str, Dependency] = {entry.name: entry for entry in entries}

    @classmethod
    def load(cls, path: str | Path) -> "ProvenanceRegistry":
        """يقرأ السجل من ملف JSON."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        entries: list[Dependency] = []
        for bucket in ("allow", "deny"):
            for item in raw.get(bucket, []):
                entries.append(
                    Dependency(
                        name=item["name"],
                        license=item["license"],
                        source=item["source"],
                        decision=bucket,
                        rationale_ar=item.get("rationale_ar", ""),
                    )
                )
        return cls(entries)

    @property
    def entries(self) -> tuple[Dependency, ...]:
        return tuple(self._entries.values())

    def decision_for(self, name: str) -> Dependency | None:
        """قرار التبعية، أو None إن لم تُسجَّل."""
        return self._entries.get(name)

    def check(self, names: Iterable[str]) -> list[str]:
        """يفحص أسماء التبعيات ويعيد قائمة المشاكل (فارغة = سليم)."""
        problems: list[str] = []
        for name in names:
            entry = self.decision_for(name)
            if entry is None:
                problems.append(
                    f"تبعية غير مسجّلة: {name} — أضف قراراً في docs/provenance/dependencies.json."
                )
            elif entry.decision == "deny":
                problems.append(
                    f"تبعية مرفوضة: {name} ({entry.license}) — {entry.rationale_ar}"
                )
        return problems
