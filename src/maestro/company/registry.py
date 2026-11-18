"""بناء سجل التشغيل من كتالوج الشركة.

الجسر بين «ما تستطيع الشركة فعله» (الكتالوج) و«ما يمكن تنفيذه الآن»
(السجل). كل قدرة في الكتالوج تصير `CapabilitySpec` قابلة للتنفيذ.
"""

from __future__ import annotations

from ..runtime.registry import CapabilityRegistry
from ..runtime.spec import CapabilitySpec
from .catalogue import CAPABILITIES, Capability, specialization_targets


def build_registry(include_specializations: bool = True) -> CapabilityRegistry:
    """يبني سجلّ القدرات من الكتالوج كاملاً."""
    registry = CapabilityRegistry()
    for capability in CAPABILITIES:
        registry.register(
            CapabilitySpec(
                name=capability.name,
                description_ar=capability.name_ar,
                required_tools=capability.tools,
                default_authority=capability.authority,
                critical=capability.critical,
            )
        )
    if include_specializations:
        # التخصّصات (مثل catalog.ingest) تُسجَّل بنسختها من القدرة الأم.
        for specialization, parent_name in specialization_targets().items():
            parent = next(c for c in CAPABILITIES if c.name == parent_name)
            registry.register(
                CapabilitySpec(
                    name=specialization,
                    description_ar=f"{parent.name_ar} — تخصّص: {specialization}",
                    required_tools=parent.tools,
                    default_authority=parent.authority,
                    critical=parent.critical,
                )
            )
    return registry


def capability_to_ir(
    capability: Capability, intent: str, *, human_approved: bool = False
) -> dict[str, object]:
    """يبني مستند IR من قدرة في الكتالوج.

    الموافقة البشرية **لا تُفترض**: قدرة صلاحيتها 3 تبقى مرفوضة (IR-04)
    ما لم يُمرَّر `human_approved=True` بعد موافقة مسجّلة فعلاً.
    """
    document: dict[str, object] = {
        "ir_version": "1.0",
        "capability": capability.name,
        "intent": intent,
        "authority": capability.authority,
        "critical": capability.critical,
        "steps": [
            {
                "id": "s1",
                "agent": capability.agent,
                "action": capability.name_ar,
                "tools": list(capability.tools),
            }
        ],
        "budget": {"max_tokens": 20_000, "max_cost_usd": 1.0, "max_wall_seconds": 300},
        "redundancy": {
            "ensemble": list(capability.ensemble),
            "min_agreement": capability.min_agreement,
        },
        "evidence": {"required": True, "artifacts": ["evidence.jsonl"]},
    }
    if human_approved:
        document["human_approval"] = True
    return document
