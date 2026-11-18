"""سجل القدرات: ما تعرفه الشركة، وبأي أدوات."""

from __future__ import annotations

from dataclasses import dataclass, field

from .spec import CapabilitySpec


@dataclass
class CapabilityRegistry:
    """سجل قدرات معلن. قدرة غير مسجّلة تُرفض قبل أي تنفيذ."""

    _specs: dict[str, CapabilitySpec] = field(default_factory=dict)

    def register(self, spec: CapabilitySpec) -> None:
        """يسجّل قدرة (أو يحدّث تعريفها)."""
        self._specs[spec.name] = spec

    def get(self, name: str) -> CapabilitySpec | None:
        """بطاقة القدرة، أو None."""
        return self._specs.get(name)

    def names(self) -> tuple[str, ...]:
        """أسماء القدرات المسجّلة."""
        return tuple(sorted(self._specs))

    def critical_names(self) -> tuple[str, ...]:
        """القدرات الحرجة (تكرار + دليل إلزامي)."""
        return tuple(sorted(name for name, spec in self._specs.items() if spec.critical))

    def __len__(self) -> int:
        return len(self._specs)
