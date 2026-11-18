#!/usr/bin/env python3
"""تشغيل قدرة واحدة من مستند IR — بالمزوّد الحقيقي أو بالفحص فقط.

الاستعمال:
    # فحص المستند فقط (بلا نموذج وبلا شبكة)
    python3 scripts/run_capability.py --ir task.json --check

    # تنفيذ حقيقي عبر DeepSeek (يحتاج DEEPSEEK_API_KEY)
    python3 scripts/run_capability.py --ir task.json --out artifacts/ --evidence evidence.jsonl

المخرج: تقرير JSON على stdout، وicode خروج 0 عند النجاح و1 عند الرفض.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from maestro.durable.journal import DurableJournal  # noqa: E402
from maestro.durable.runner import DurableRunner  # noqa: E402
from maestro.evidence.log import EvidenceLog  # noqa: E402
from maestro.guards.budget import BudgetGuard  # noqa: E402
from maestro.guards.permission import PermissionGuard  # noqa: E402
from maestro.ir.validate import errors_only, validate_ir  # noqa: E402
from maestro.routing.base import RoutingPolicy  # noqa: E402
from maestro.routing.deepseek import deepseek_flash_profile  # noqa: E402
from maestro.routing.http_provider import OpenAICompatibleProvider  # noqa: E402
from maestro.routing.router import ModelRouter  # noqa: E402
from maestro.runtime.runner import CapabilityRunner  # noqa: E402

#: قدرات مسموح بها افتراضياً في أداة التشغيل.
DEFAULT_CAPABILITIES = ("media.render", "catalog.ingest", "media.caption")


def main() -> int:
    """ينفّذ الطلب ويطبع التقرير."""
    parser = argparse.ArgumentParser(description="تشغيل قدرة واحدة من مستند IR.")
    parser.add_argument("--ir", required=True, help="مسار مستند IR بصيغة JSON")
    parser.add_argument("--check", action="store_true", help="فحص المستند فقط بلا تنفيذ")
    parser.add_argument("--out", default=None, help="مجلد المخرجات")
    parser.add_argument("--evidence", default="evidence.jsonl", help="ملف سجل الأدلة")
    parser.add_argument("--journal", default="journal.jsonl", help="ملف سجل المتانة")
    parser.add_argument("--task-id", default="cli-task", help="معرّف المهمة")
    parser.add_argument(
        "--allow",
        action="append",
        default=None,
        help="قدرة مسموح بها (يمكن تكرارها)",
    )
    args = parser.parse_args()

    doc = json.loads(Path(args.ir).read_text(encoding="utf-8"))

    if args.check:
        findings = validate_ir(doc)
        print(json.dumps([f.as_dict() for f in findings], ensure_ascii=False, indent=2))
        if errors_only(findings):
            print("رُفض المستند: القواعد المكسورة أعلاه.")
            return 1
        print("المستند سليم: يجتاز كل القواعد.")
        return 0

    from maestro.integrations.nasma.pipeline import default_registry

    registry = default_registry()
    profile = deepseek_flash_profile()
    router = ModelRouter(
        providers={"deepseek": OpenAICompatibleProvider(name="deepseek")},
        profiles={"deepseek": profile},
        policy=RoutingPolicy(),
        budget=BudgetGuard(max_cost_usd=5.0, max_tokens=500_000),
    )
    permissions = PermissionGuard(
        allowed_capabilities=frozenset(args.allow or DEFAULT_CAPABILITIES),
        max_authority=2,
    )
    capability_runner = CapabilityRunner(registry, router, permissions, EvidenceLog(args.evidence))
    runner = DurableRunner(capability_runner, DurableJournal(args.journal))

    outcome = runner.execute(args.task_id, doc)
    report = outcome.report.as_dict()
    report["status"] = outcome.status
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "output.txt").write_text(outcome.report.output or "", encoding="utf-8")
        (out_dir / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"كُتبت المخرجات في {out_dir}")

    return 0 if outcome.report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
