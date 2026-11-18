"""عقود القدرات: من الكتالوج إلى مستند IR قابل للتنفيذ.

هذا هو الجسر الأخير بين **ما تستطيع الشركة فعله** (الكتالوج) و**ما يمكن
تنفيذه الآن** (مستند IR يجتاز القواعد). لكل قدرة في الكتالوج عقد واحد
مولَّد، وكل عقد يُفحصagainst القواعد ومقارَن بالكتالوج.

ولأن العقد **مولَّدة**، لا تنحرف عن الكتالوج إلا إذا انحرف الكود.
"""

from __future__ import annotations

from typing import Any

from ..ir.validate import validate_ir
from .catalogue import CAPABILITIES, Capability

#: نيّة افتراضية تُستعمل في توليد العقد.
DEFAULT_INTENT = "تنفيذ هذه القدرة بحسب عقدتها"


def contract_for(capability: Capability, intent: str = DEFAULT_INTENT) -> dict[str, Any]:
    """يبني مستند IR لقدرة من الكتالوج."""
    document: dict[str, Any] = {
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
    return document


def all_contracts() -> dict[str, dict[str, Any]]:
    """عقود كل القدرات، مفهرسة بالاسم."""
    return {capability.name: contract_for(capability) for capability in CAPABILITIES}


def check_contracts() -> list[str]:
    """يفحص كل عقد ويعيد المشاكل (فارغة = سليم).

    ثلاث قواعد: العقد يجتاز قواعد IR، والوكيل والأدوات والسلاحية مطابقة
    للكتالوج، والقدرات الحرجة تحمل agreement وevidence.
    """
    problems: list[str] = []
    for capability in CAPABILITIES:
        document = contract_for(capability)
        errors = [f for f in validate_ir(document) if f.severity == "error"]
        if capability.authority >= 3:
            # الصلاحية 3 **لا تُفترض**: العقد بلا موافقة مرفوض بالضبط
            # بالقاعدة IR-04، وبموافقة مسجّلة يمرّ. وهذا سلوك مقصود.
            if [error.rule_id for error in errors] != ["IR-04"]:
                problems.append(
                    f"عقد «{capability.name}»: صلاحية 3 يجب أن تُرفض بـIR-04 وحده، "
                    f"ورُفضت بـ{[error.rule_id for error in errors]}."
                )
            approved = contract_for(capability)
            approved["human_approval"] = True
            approved_errors = [
                f for f in validate_ir(approved) if f.severity == "error"
            ]
            for error in approved_errors:
                problems.append(
                    f"عقد «{capability.name}» بعد الموافقة: {error.rule_id} — {error.message_ar}"
                )
        else:
            for error in errors:
                problems.append(
                    f"عقد «{capability.name}»: {error.rule_id} — {error.message_ar}"
                )
        steps = document.get("steps") or []
        if steps:
            step = steps[0]
            if step.get("agent") != capability.agent:
                problems.append(f"عقد «{capability.name}»: الوكيل لا يطابق الكتالوج.")
            if list(step.get("tools", [])) != list(capability.tools):
                problems.append(f"عقد «{capability.name}»: الأدوات لا تطابق الكتالوج.")
        if document.get("authority") != capability.authority:
            problems.append(f"عقد «{capability.name}»: مستوى الصلاحية لا يطابق الكتالوج.")
    return problems
