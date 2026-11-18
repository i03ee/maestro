#!/usr/bin/env python3
"""توليد وثيقة عقود القدرات — أو فحصها.

    python3 scripts/contracts_report.py            # يكتب
    python3 scripts/contracts_report.py --check    # يفشل إن انحرفت
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from maestro.company.contracts import all_contracts, check_contracts  # noqa: E402

DOC_PATH = ROOT / "docs" / "CAPABILITY_CONTRACTS.json"


def render() -> str:
    """يبني نص الوثيقة (حتمي)."""
    contracts = all_contracts()
    payload = {
        "generated_from": "src/maestro/company/catalogue.py",
        "count": len(contracts),
        "contracts": contracts,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    """يكتب أو يفحص."""
    parser = argparse.ArgumentParser(description="عقود القدرات.")
    parser.add_argument("--check", action="store_true", help="افحص دون كتابة")
    args = parser.parse_args()

    problems = check_contracts()
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1

    text = render()
    if args.check:
        if not DOC_PATH.is_file():
            print(f"FAIL: الوثيقة مفقودة: {DOC_PATH}")
            return 1
        if DOC_PATH.read_text(encoding="utf-8") != text:
            print("FAIL: انحراف بين وثيقة العقود والشيفرة.")
            return 1
        print(f"سيرى العقود: {len(all_contracts())} عقداً مطابقاً للشيفرة.")
        return 0

    DOC_PATH.write_text(text, encoding="utf-8")
    print(f"كُتبت الوثيقة: {DOC_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
