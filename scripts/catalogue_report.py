#!/usr/bin/env python3
"""توليد وثيقة كتالوج الشركة من الشيفرة — أو فحصها ضد الشيفرة.

    python3 scripts/catalogue_report.py            # يكتب الوثيقة
    python3 scripts/catalogue_report.py --check    # يفحص: يفشل إن انحرفت

الوثيقة مولَّدة: أي انحراف بين الكود والوثيقة يُفشل البوابة. لا نصّ يُكتب
بيد ويبقى دون فحص.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from maestro.company.catalogue import (  # noqa: E402
    CAPABILITIES,
    COMMUNITY_GATE,
    DOMAINS,
    GATE_INVOCATIONS,
    by_domain,
)
from maestro.company.topology import edges, topology_report  # noqa: E402

DOC_PATH = ROOT / "docs" / "CAPABILITY_CATALOGUE.md"

GOVERNING_RULES: tuple[str, ...] = (
    "**مركز واحد، ذراعان.** نقطة مركزية واحدة تدير النطاقات الثمانية، "
    "ومعاها مساعد التحليل ومساعد التحقق. لا مركزان.",
    "**ثمانية نطاقات، لا 24 وكيلاً متقطعاً.** كل نطاق مديره واحد يملك "
    "ميزانيته وصلاحياته، ويصدر «قرار نطاق» يُعتمد من المركز.",
    "**الاعتماد المتبادل بدل التسلسل.** البوابات ليست في آخر الطريق: "
    "بوابة الفكرة تسبق البناء، وبوابة الواجهة تسبق التسليم، وبوابة التسعير "
    "تسبق الحدود، وبوابة الدفع تسبق الإصدار.",
    "**قدرة واحدة = وكيل واحد = عقد واحد.** من يحتاج ذاكرة خاصة فهو "
    "**استدعاء إضافي** لقدرة موجودة، لا قدرة جديدة.",
    "**القدرة الحرجة لا تُقبل بنموذج واحد.** تُنفَّذ بنموذجين مستقلين "
    "ويُقبل الناتج باتفاقهما — شرط قابل للاختبار لا انطباع.",
)


def render() -> str:
    """يبني نص الوثيقة (حتمي: نفس المدخلات ⇒ نفس النص)."""
    report = topology_report()
    grouped = by_domain()
    lines: list[str] = []
    lines.append("# كتالوج الشركة")
    lines.append("")
    lines.append("> وثيقة **مولَّدة** من `src/maestro/company/catalogue.py`.")
    lines.append("> لا تُحرَّر بيد: `python3 scripts/catalogue_report.py --check`")
    lines.append("> يفشل البوابة إن انحرف محتوى هذه الصفحة عن الشيفرة.")
    lines.append("")
    lines.append("## القواعد الخمس الحاكمة")
    lines.append("")
    for index, rule in enumerate(GOVERNING_RULES, start=1):
        lines.append(f"{index}. {rule}")
    lines.append("")
    lines.append("## الأرقام")
    lines.append("")
    lines.append(f"- النطاقات: **{report['domains']}**")
    lines.append(f"- القدرات: **{report['capabilities']}**")
    lines.append(f"- البوابات: **{report['gates']}**")
    lines.append(f"- وصلات الاعتماد: **{report['edges']}**")
    lines.append(f"- القدرات الحرجة: **{report['critical']}**")
    lines.append(f"- مواضع استدعاء بوابة المجتمع: **{report['community_gate_invocations']}**")
    lines.append("")
    lines.append("## النطاقات")
    lines.append("")
    lines.append("| النطاق | المهمة | المدير | القدرات |")
    lines.append("|---|---|---|---|")
    for domain in DOMAINS:
        count = len(grouped.get(domain.key, ()))
        lines.append(f"| {domain.name_ar} (`{domain.key}`) | {domain.mission_ar} | `{domain.director_agent}` | {count} |")
    lines.append("")
    lines.append("## القدرات")
    lines.append("")
    lines.append("| القدرة | الوكيل | صلاحية | حرجة | النموذج ١ | شرط النقل | البوابات |")
    lines.append("|---|---|---|---|---|---|---|")
    for capability in CAPABILITIES:
        gates = "، ".join(f"`{gate}`" for gate in capability.gates) or "—"
        lines.append(
            f"| `{capability.name}`<br/>{capability.name_ar} | `{capability.agent}` | "
            f"{capability.authority} | {'نعم' if capability.critical else 'لا'} | "
            f"`{capability.ensemble[0]}` | {capability.fallback_condition_ar} | {gates} |"
        )
    lines.append("")
    lines.append("## بوابة المجتمع: قدرة واحدة، أربعة استدعاءات")
    lines.append("")
    lines.append(f"البوابة: `{COMMUNITY_GATE}` — قدرة واحدة بذاكرة واحدة.")
    lines.append("")
    for index, invocation in enumerate(GATE_INVOCATIONS, start=1):
        lines.append(f"{index}. `{invocation}`")
    lines.append("")
    lines.append("## شبكة الاعتماد")
    lines.append("")
    lines.append("| يحتاج | بوابته |")
    lines.append("|---|---|")
    for edge in sorted(edges(), key=lambda item: (item.source, item.target)):
        lines.append(f"| `{edge.source}` | `{edge.target}` |")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    """يكتب الوثيقة أو يفحصها."""
    parser = argparse.ArgumentParser(description="توليد كتالوج الشركة.")
    parser.add_argument("--check", action="store_true", help="افحص دون كتابة")
    parser.add_argument("--out", default=str(DOC_PATH), help="مسار الوثيقة")
    args = parser.parse_args()

    text = render()
    target = Path(args.out)
    if args.check:
        if not target.is_file():
            print(f"FAIL: الوثيقة مفقودة: {target}")
            return 1
        current = target.read_text(encoding="utf-8")
        if current != text:
            print("FAIL: انحراف بين الوثيقة والشيفرة. شغّل: scripts/catalogue_report.py")
            return 1
        print(f"سيرى الكتالوج: الوثيقة مطابقة للشيفرة ({len(CAPABILITIES)} قدرة).")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"كُتبت الوثيقة: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
