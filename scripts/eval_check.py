#!/usr/bin/env python3
"""تشغيل مجموعات التقييم.

    python3 scripts/eval_check.py

كل حالة تجتاز أو تفشل. لا نسبة نجاح: فشل واحد ⇒ الفحص يفشل.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from maestro.evals import CASES, run_all_cases  # noqa: E402
from maestro.evals.cases import coverage_report  # noqa: E402


def main() -> int:
    """يشغّل الحالات ويطبع الجدول."""
    outcomes = run_all_cases()
    failures = 0
    for outcome in outcomes:
        mark = "تجتاز" if outcome.ok else "فشل"
        if not outcome.ok:
            failures += 1
        print(f"{outcome.case_id:32s} {mark}")
        for problem in outcome.problems:
            print(f"    {problem}")
    coverage = coverage_report()
    print()
    print("تغطية التقييم:")
    print(f"  مقيَّمة من الكتالوج: {len(coverage['covered'])}")
    print(f"  مؤجَّلة بسبب مكتوب: {len(coverage['deferred'])}")
    print(f"  خارج الكتالوج (تخصّص/توضيحية): {len(coverage['covered_extra'])}")
    if coverage["missing"]:
        for name in coverage["missing"]:
            print(f"FAIL: قدرة بلا حالة تقييم ولا سبب تأجيل: {name}")
    if coverage["unknown_deferrals"]:
        for name in coverage["unknown_deferrals"]:
            print(f"FAIL: تأجيل لقدرة غير موجودة في الكتالوج: {name}")
    print()
    print(f"الحالات: {len(outcomes)} · الفاشلة: {failures}")
    return 1 if (failures or coverage["missing"] or coverage["unknown_deferrals"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
