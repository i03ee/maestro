#!/usr/bin/env python3
"""تشغيل شواهد معايير القبول AC-01..AC-20.

    python3 scripts/verify_acceptance.py             # يشغّل الشواهد ويطبع الجدول
    python3 scripts/verify_acceptance.py --write-docs # يحدّث وثيقة الدليل
    python3 scripts/verify_acceptance.py --check-docs # يفحص انحراف الوثيقة

رمز الخروج: 0 إذا اجتاز كل الشواهد المنفَّذة، و1 إن فشل واحد. المعايير غير
المنفَّذة تُعلَن **غير مُثبَتة بعد** مع سبب النقص — لا تُحسب نجاحاً.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from maestro.acceptance.criteria import CRITERIA  # noqa: E402
from maestro.acceptance.proofs import PROOFS, run_all_proofs  # noqa: E402

DOC_PATH = ROOT / "docs" / "AC_EVIDENCE.md"


def render_documentation() -> str:
    """يبني وثيقة الدليل (ثابتة: لا تعتمد على نتائج التشغيل)."""
    lines: list[str] = []
    lines.append("# دليل معايير القبول AC-01..AC-20")
    lines.append("")
    lines.append("> وثيقة **مولَّدة** من `src/maestro/acceptance/criteria.py`.")
    lines.append("> النتائج الحيّة تُشغَّل بـ`python3 scripts/verify_acceptance.py`.")
    lines.append("")
    proven = [c for c in CRITERIA if c.implemented]
    pending = [c for c in CRITERIA if not c.implemented]
    lines.append(
        f"معايير لها شاهد منفَّذ: **{len(proven)}** من {len(CRITERIA)} — "
        f"والمتبقّي **{len(pending)}** غير مُثبَت بعد (مع سبب النقص)."
    )
    lines.append("")
    lines.append("| المعيار | العنوان | الدليل المسمّى | الحالة | الشاهد |")
    lines.append("|---|---|---|---|---|")
    for criterion in CRITERIA:
        if criterion.implemented:
            state = "مُثبَت"
            proof = f"`{criterion.proof_key}`"
        else:
            state = "غير مُثبَت بعد"
            proof = criterion.not_proven_reason_ar
        lines.append(
            f"| {criterion.id} | {criterion.title_ar} | `{criterion.artefact}` | {state} | {proof} |"
        )
    lines.append("")
    lines.append("## المعايير غير المُثبَتة بعد")
    lines.append("")
    for criterion in pending:
        lines.append(f"- **{criterion.id} — {criterion.title_ar}**: {criterion.not_proven_reason_ar}")
    lines.append("")
    lines.append("## اختبار الحقن (AC-12 وAC-14)")
    lines.append("")
    lines.append(
        "نحقن عيباً متعمّداً في **نسخة** من الشيفرة — نحذف فحص الصلاحية في "
        "`guards/permission.py` — ثم نطالب المفتّش بأن يرفض النسخة المعطوبة "
        "ويقبل السليمة. إن قبل المعطوبة ⇒ النظام غير جاهز. هذا هو اختبار "
        "القبول رقم واحد في وثيقة المتطلبات."
    )
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    """يشغّل الشواهد ويطبع الجدول."""
    parser = argparse.ArgumentParser(description="شواهد معايير القبول.")
    parser.add_argument("--write-docs", action="store_true", help="يحدّث وثيقة الدليل")
    parser.add_argument("--check-docs", action="store_true", help="يفحص انحراف الوثيقة")
    args = parser.parse_args()

    if args.write_docs:
        DOC_PATH.write_text(render_documentation(), encoding="utf-8")
        print(f"كُتبت الوثيقة: {DOC_PATH}")
        return 0
    if args.check_docs:
        if not DOC_PATH.is_file():
            print(f"FAIL: الوثيقة مفقودة: {DOC_PATH}")
            return 1
        if DOC_PATH.read_text(encoding="utf-8") != render_documentation():
            print("FAIL: انحراف بين وثيقة القبول والشيفرة.")
            return 1
        print("سيرى القبول: الوثيقة مطابقة للشيفرة.")
        return 0

    results = dict(run_all_proofs())
    failures = 0
    for criterion in CRITERIA:
        if not criterion.implemented:
            print(f"{criterion.id}  غير مُثبَت بعد   {criterion.title_ar}")
            print(f"      السبب: {criterion.not_proven_reason_ar}")
            continue
        result = results.get(criterion.proof_key or "")
        if result is None:
            print(f"{criterion.id}  لا شاهد   {criterion.title_ar}")
            failures += 1
            continue
        mark = "مُثبَت" if result.ok else "فشل"
        if not result.ok:
            failures += 1
        print(f"{criterion.id}  {mark:10s}  {criterion.title_ar}")
        print(f"      {result.detail_ar}")

    implemented = sum(1 for c in CRITERIA if c.implemented)
    pending = len(CRITERIA) - implemented
    print()
    print(f"المعايير: {implemented} مُثبَت + {pending} غير مُثبَت = {len(CRITERIA)}")
    print(f"الشواهد الفاشلة: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
