#!/usr/bin/env python3
"""تشغيل كل البوابات بالترتيب في أمر واحد.

    python3 scripts/verify_all.py [--json reports/verify_all.json]

الترتيبFixed: من ثوابت المستودع (الأساس) إلى الشواهد (الأعلى). وكل بوابة
**ثنائية** — تفشل يتوقف التصعيد ويبقى سببها مكتوباً.

هذا هو الأمر الذي يُشغَّل قبل أي دمج، والأمر الذي يوثّق حالة المشروع.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Gate:
    """بوابة واحدة."""

    name: str
    command: tuple[str, ...]


GATES: tuple[Gate, ...] = (
    Gate("ثوابت المستودع", (sys.executable, "scripts/validate_repo.py")),
    Gate("التراخيص", (sys.executable, "scripts/check_licenses.py")),
    Gate("كتالوج الشركة", (sys.executable, "scripts/catalogue_report.py", "--check")),
    Gate("عقود القدرات", (sys.executable, "scripts/contracts_report.py", "--check")),
    Gate("دليل القبول", (sys.executable, "scripts/verify_acceptance.py", "--check-docs")),
    Gate("شواهد القبول", (sys.executable, "scripts/verify_acceptance.py")),
    Gate("مجموعات التقييم", (sys.executable, "scripts/eval_check.py")),
    Gate("مقياس الحمل", (sys.executable, "scripts/load_check.py", "--requests", "80", "--concurrency", "16")),
)


def run_gate(gate: Gate) -> dict[str, object]:
    """يشغّل بوابة ويعيد نتيجتها."""
    started = time.perf_counter()
    result = subprocess.run(
        list(gate.command), cwd=ROOT, capture_output=True, text=True
    )
    elapsed = (time.perf_counter() - started) * 1000
    output = (result.stdout + result.stderr).strip()
    tail = output.splitlines()[-1] if output else ""
    return {
        "gate": gate.name,
        "command": " ".join(gate.command),
        "ok": result.returncode == 0,
        "exit_code": result.returncode,
        "duration_ms": round(elapsed),
        "last_line": tail,
        "output": output,
    }


def main() -> int:
    """يشغّل كل البوابات ويطبع الجدول."""
    parser = argparse.ArgumentParser(description="كل البوابات في أمر واحد.")
    parser.add_argument("--json", dest="json_path", default=None, help="مسار تقرير JSON")
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="توقّف عند أول بوابة فاشلة (الافتراضي: تشغيل الكل)",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="بوابات محددة فقط، مفصولة بفواصل (مثال: ثوابت المستودع,التراخيص)",
    )
    args = parser.parse_args()

    gates = GATES
    if args.only:
        wanted = {name.strip() for name in args.only.split(",") if name.strip()}
        unknown = wanted - {gate.name for gate in GATES}
        if unknown:
            print(f"FAIL: بوابات غير معروفة: {'، '.join(sorted(unknown))}")
            return 1
        gates = tuple(gate for gate in GATES if gate.name in wanted)

    results: list[dict[str, object]] = []
    for gate in gates:
        outcome = run_gate(gate)
        results.append(outcome)
        mark = "✔" if outcome["ok"] else "✘"
        print(f"{mark} {outcome['gate']:20s} {outcome['duration_ms']:>6}ms  {outcome['last_line']}")
        if not outcome["ok"] and args.stop_on_failure:
            break

    failed = [outcome for outcome in results if not outcome["ok"]]
    print()
    print(f"البوابات: {len(results)} · الفاشلة: {len(failed)}")
    for outcome in failed:
        print(f"✘ {outcome['gate']}: {outcome['last_line']}")

    if args.json_path:
        path = Path(args.json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"gates": results, "failed": len(failed)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"التقرير: {path}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
