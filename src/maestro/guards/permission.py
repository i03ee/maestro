"""حارس الصلاحيات: ما يُسمح، ومن يوافق، وأين تُسجَّل الموافقة."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Decision:
    """قرار صلاحية: مسموح أو مرفوض، مع سبب مكتوب."""

    allowed: bool
    reason_ar: str
    capability: str
    authority: int

    def as_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "reason_ar": self.reason_ar,
            "capability": self.capability,
            "authority": self.authority,
        }


@dataclass
class PermissionGuard:
    """يسمح بالقدرات المصرّح بها فقط، وبمستوى صلاحية لا يتجاوز السقف."""

    allowed_capabilities: frozenset[str] = frozenset()
    max_authority: int = 2
    approved_capabilities: frozenset[str] = field(default_factory=frozenset)

    def authorize(self, capability: str, authority: int, *, human_approved: bool = False) -> Decision:
        """يفحص الطلب. الرفض نهائي: لا يوجد مسار «تخطّي»."""
        if capability not in self.allowed_capabilities:
            return Decision(
                False,
                f"القدرة غير مصرّح بها: {capability}.",
                capability,
                authority,
            )
        if authority > self.max_authority:
            return Decision(
                False,
                f"مستوى الصلاحية {authority} يتجاوز السقف المسموح {self.max_authority}.",
                capability,
                authority,
            )
        if authority >= 3 and not (human_approved or capability in self.approved_capabilities):
            return Decision(
                False,
                "الصلاحية 3 تتطلب موافقة بشرية مسجّلة.",
                capability,
                authority,
            )
        return Decision(True, "مسموح ضمن النطاق المصرّح به.", capability, authority)
