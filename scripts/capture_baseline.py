#!/usr/bin/env python3
"""أداة تسجيل الخط الأساسي البشري.

قبل أن نقول «الوكيل أسرع»، نعرف كم كان الإنسان يستغرق. هذه الأداة تسجّل
القياس البشري لكل مخرج: الزمن بالدقائق، وهل قُبل الناتج دون تحرير، وهل
تكرّر الطلب خلال أسبوعين.

الأرقام **وصف** للمقارنة بخط الأساس، لا بوابة قبول للشيفرة (PROTOCOL.md).

الاستعمال:
    python3 scripts/capture_baseline.py \
        --capability catalog.ingest \
        --output-id sku-001 \
        --human-minutes 12 \
        --accepted-unedited \
        --repeat-within-2-weeks no \
        --file baseline.jsonl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from maestro.baseline.recorder import BaselineRecorder  # noqa: E402


def main() -> int:
    """يسجّل قياساً واحداً ويطبع ملخّص الخط الأساس."""
    parser = argparse.ArgumentParser(description="تسجيل خط أساسي بشري لمخرج واحد.")
    parser.add_argument("--capability", required=True, help="معرّف القدرة")
    parser.add_argument("--output-id", required=True, help="معرّف المخرج")
    parser.add_argument("--human-minutes", required=True, type=float, help="الزمن بالدقائق")
    parser.add_argument("--cost-usd", type=float, default=0.0, help="تكلفة المخرج بالدولار")
    parser.add_argument(
        "--accepted-unedited",
        choices=("yes", "no"),
        required=True,
        help="هل قُبل المخرج دون تحرير",
    )
    parser.add_argument(
        "--repeat-within-2-weeks",
        choices=("yes", "no", "unknown"),
        default="unknown",
        help="هل تكرّر الطلب خلال أسبوعين",
    )
    parser.add_argument(
        "--file",
        default="baseline.jsonl",
        help="ملف السجل (افتراضياً baseline.jsonl)",
    )
    parser.add_argument("--timestamp", default=None, help="الطابع الزمني (ISO-8601)")
    args = parser.parse_args()

    from datetime import datetime, timezone

    timestamp = args.timestamp or datetime.now(timezone.utc).isoformat()
    repeat = None if args.repeat_within_2_weeks == "unknown" else args.repeat_within_2_weeks == "yes"

    recorder = BaselineRecorder(args.file)
    record = recorder.record(
        capability=args.capability,
        output_id=args.output_id,
        human_minutes=args.human_minutes,
        cost_usd=args.cost_usd,
        accepted_unedited=args.accepted_unedited == "yes",
        repeat_within_2_weeks=repeat,
        timestamp=timestamp,
    )
    summary = recorder.summary(args.capability)
    print(f"سُجّل: {record.output_id} — {record.human_minutes} دقيقة")
    print(
        f"خط الأساس للقدرة «{args.capability}»: "
        f"{summary['outputs']} مخرجاً، "
        f"متوسط {summary['mean_human_minutes']:.1f} دقيقة، "
        f"متوسط التكلفة {summary['mean_cost_usd']:.3f}$."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
