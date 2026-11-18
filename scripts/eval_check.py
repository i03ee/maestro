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
    print()
    print(f"الحالات: {len(outcomes)} · الفاشلة: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
