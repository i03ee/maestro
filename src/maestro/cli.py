"""واجهة سطر الأوامر: نقطة دخول المشروع لا الدوال وحدها.

    python3 -m maestro run "فكرة جديدة" --out cli
    python3 -m maestro scaffold --out workspace --project demo

كل أمر يكتب artefact مسمّى في وثيقة القبول (AC-01 وAC-08)، فيمكن فحص
الناتج آلياً بدل الثقة بالنص.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .company.catalogue import capability_by_name
from .company.registry import capability_to_ir
from .ir.validate import validate_ir


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def command_run(args: argparse.Namespace) -> int:
    """يستقبل فكرة، ينشئ لها مشروعاً ومستند IR، ويكتب تقرير التحقق."""
    out_dir = Path(args.out)
    project_id = args.project_id or f"prj-{uuid.uuid4().hex[:12]}"
    capability = capability_by_name(args.capability)
    if capability is None:
        print(f"FAIL: قدرة غير معروفة: {args.capability}", file=sys.stderr)
        return 1

    intent = args.idea if len(args.idea) >= 8 else args.idea + " — توسيع النيّة"
    document = capability_to_ir(capability, intent, human_approved=args.human_approved)
    findings = validate_ir(document)

    _write_json(
        out_dir / "run_request.json",
        {
            "project_id": project_id,
            "idea": args.idea,
            "capability": capability.name,
            "created_at": _now(),
            "status": "accepted" if not [f for f in findings if f.severity == "error"] else "rejected",
        },
    )
    _write_json(out_dir / "ir" / "appir.json", document)
    _write_json(
        out_dir / "ir" / "validate_report.json",
        [finding.as_dict() for finding in findings],
    )

    errors = [finding for finding in findings if finding.severity == "error"]
    print(f"project_id: {project_id}")
    print(f"القدرة: {capability.name} — {capability.name_ar}")
    print(f"مستند IR: {out_dir / 'ir' / 'appir.json'}")
    if errors:
        print(f"رُفض المستند بـ{len(errors)} قاعدة:")
        for finding in errors:
            print(f"  - {finding.rule_id}: {finding.message_ar}")
        return 1
    print(f"اجتاز المستند كل القواعد ({len(findings)} ملاحظة).")
    return 0


def command_scaffold(args: argparse.Namespace) -> int:
    """ينشئ هيكل مشروع من الكتالوج."""
    out_dir = Path(args.out)
    manifest = {
        "project_id": args.project_id or "demo",
        "created_at": _now(),
        "domains": [],
        "capabilities": [],
        "directories": [
            "apps/web",
            "apps/mobile",
            "packages/core",
            "docs",
            "tests",
            "workspace",
        ],
    }
    for relative in manifest["directories"]:
        (out_dir / relative).mkdir(parents=True, exist_ok=True)
    (out_dir / "docs" / "README.md").write_text(
        "# المشروع\n\nهيكل مولَّد من كتالوج MAESTRO.\n", encoding="utf-8"
    )
    _write_json(out_dir / "manifest.json", manifest)
    print(f"كُتمل الهيكل في {out_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """محرّك الأوامر."""
    parser = argparse.ArgumentParser(prog="maestro", description="شركة مصغّرة من الوكلاء.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="استقبل فكرة وافتح مشروعاً")
    run.add_argument("idea", help="نص الفكرة")
    run.add_argument("--out", default="cli", help="مجلد المخرجات")
    run.add_argument("--project-id", default=None, help="معرّف مشروع محدّد (للاختبار)")
    run.add_argument(
        "--capability", default="commercial.idea_framing", help="القدرة المستقبِلة"
    )
    run.add_argument(
        "--human-approved", action="store_true", help="تسجيل موافقة بشرية للصلاحية 3"
    )
    run.set_defaults(func=command_run)

    scaffold = sub.add_parser("scaffold", help="أنشئ هيكل مشروع")
    scaffold.add_argument("--out", default="workspace", help="مجلد الهيكل")
    scaffold.add_argument("--project-id", default=None, help="معرّف المشروع")
    scaffold.set_defaults(func=command_scaffold)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """نقطة الدخول."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
