"""الطوبولوجيا: الاعتماد المتبادل بين النطاقات، وبوابة واحدة بأربعة استدعاءات.

الاعتماد المتبادل هو ما يحوّل «مساراً» إلى «شبكة»: قدرة تعتمد على أخرى
-dependency- قبل أن تُنفَّذ، وكل بوابة تُعيد العمل من حيث انطلق بدل أن تُسقط
ما بعدها.

هنا شيءان منفصلان يُخلَط بينهما عادةً:
- **البوابة** (`gate`): قدرة تُستدعى قبل غيرها.
- **الاستدعاء** (`invocation`): الموضع الذي تُستدعى فيه البوابة.
  البوابة الواحدة تُستدعى في أربعة مواضع — وهذا هو الفرق بين «بوابة واحدة
  بأربع ذاكرات» و«قدرة واحدة بأربع استدعاءات».
"""

from __future__ import annotations

from dataclasses import dataclass

from .catalogue import (
    CAPABILITIES,
    COMMUNITY_GATE,
    GATE_INVOCATIONS,
    Capability,
    capability_by_name,
)


@dataclass(frozen=True)
class Edge:
    """وصلة اعتماد: من يحتاج، وإلى أي قدرة."""

    source: str
    target: str

    def as_dict(self) -> dict[str, str]:
        return {"source": self.source, "target": self.target}


def edges() -> tuple[Edge, ...]:
    """كل وصلات الاعتماد في الشبكة."""
    result: list[Edge] = []
    for capability in CAPABILITIES:
        for gate in capability.gates:
            result.append(Edge(source=capability.name, target=gate))
    return tuple(result)


def incoming_edges(name: str) -> tuple[Edge, ...]:
    """الوصلات التي تنتهي عند قدرة معيّنة."""
    return tuple(edge for edge in edges() if edge.target == name)


def outgoing_edges(name: str) -> tuple[Edge, ...]:
    """الوصلات التي تبدأ من قدرة معيّنة."""
    return tuple(edge for edge in edges() if edge.source == name)


def community_gate_invocations() -> tuple[str, ...]:
    """المواضع الأربعة التي تُستدعى فيها بوابة المجتمع."""
    return GATE_INVOCATIONS


def check_catalogue() -> list[str]:
    """يفحص كتالوج الشركة ويعيد قائمة المشاكل (فارغة = سليم).

    الفحوص كلها ثنائية: كل قاعدة تُرجع نعم/لا، ولاexists عتبة نسبية.
    """
    problems: list[str] = []

    # 1) الأعداد المعلنة
    if len(CAPABILITIES) != 24:
        problems.append(f"عدد القدرات {len(CAPABILITIES)} لا يساوي 24.")
    if len({capability.domain for capability in CAPABILITIES}) != 8:
        problems.append("عدد النطاقات المستعملة ليس 8.")

    # 2) التفرّد
    names = [capability.name for capability in CAPABILITIES]
    if len(set(names)) != len(names):
        problems.append("يوجد معرّف قدرة مكرر.")
    agents = [capability.agent for capability in CAPABILITIES]
    if len(set(agents)) != len(agents):
        problems.append("يوجد وكيل واحد مخصّص لأكثر من قدرة — قاعدة «قدرة = وكيل» مكسورة.")

    # 3) كل نطاق يملك قدرة واحدة على الأقل
    from .catalogue import DOMAINS, by_domain

    grouped = by_domain()
    for domain in DOMAINS:
        if not grouped.get(domain.key):
            problems.append(f"النطاق «{domain.key}» بلا قدرات.")

    # 4) كل بوابة указаت لقدرة موجودة
    for capability in CAPABILITIES:
        for gate in capability.gates:
            if capability_by_name(gate) is None:
                problems.append(
                    f"القدرة «{capability.name}» تشير إلى بوابة غير موجودة: {gate}."
                )

    # 5) القدرات الحرجة: نموذجان على الأقل واتفاق نموذجين
    for capability in CAPABILITIES:
        if not capability.critical:
            continue
        if len(capability.ensemble) < 2:
            problems.append(f"القدرة الحرجة «{capability.name}» بلا نموذج احتياطي.")
        if capability.min_agreement < 2:
            problems.append(
                f"القدرة الحرجة «{capability.name}» تقبل نموذجاً واحداً (min_agreement < 2)."
            )
        # القدرة التي **هي** بوابة (تستدعيها غيرها) هي البوابة نفسها،
        # فلا يُطلب منها أن تمرّ ببوابة أخرى.
        gate_names = {edge.target for edge in edges()}
        if capability.name not in gate_names and not capability.gates:
            problems.append(f"القدرة الحرجة «{capability.name}» بلا بوابة.")

    # 6) بوابة المجتمع: قدرة واحدة، أربعة استدعاءات
    if capability_by_name(COMMUNITY_GATE) is None:
        problems.append("بوابة المجتمع غير معرَّفة.")
    if len(set(GATE_INVOCATIONS)) != 4:
        problems.append("عدد مواضع استدعاء بوابة المجتمع ليس 4.")
    for invocation in GATE_INVOCATIONS:
        capability = capability_by_name(invocation)
        if capability is None:
            problems.append(f"موضع استدعاء غير موجود: {invocation}.")
        elif COMMUNITY_GATE not in capability.gates:
            problems.append(f"«{invocation}» لا يستدعي بوابة المجتمع.")

    # 7) لا وصلات معلّقة: كل بوابة تُستدعى فعلاً
    used_gates = {edge.target for edge in edges()}
    for gate in used_gates:
        if capability_by_name(gate) is None:
            problems.append(f"بوابة معلّقة بلا قدرة: {gate}.")

    # 8) الأدوات ضمن القائمة المسموحة
    from ..ir.validate import ALLOWED_TOOLS

    for capability in CAPABILITIES:
        for tool in capability.tools:
            if tool not in ALLOWED_TOOLS:
                problems.append(
                    f"القدرة «{capability.name}» تستعمل أداة خارج القائمة المسموحة: {tool}."
                )

    return problems


def topology_report() -> dict[str, object]:
    """ملخّص الطوبولوجيا (للتقارير والوثائق)."""
    return {
        "domains": len({capability.domain for capability in CAPABILITIES}),
        "capabilities": len(CAPABILITIES),
        "gates": len({edge.target for edge in edges()}),
        "edges": len(edges()),
        "critical": len([c for c in CAPABILITIES if c.critical]),
        "community_gate_invocations": len(GATE_INVOCATIONS),
    }
