#!/usr/bin/env python3
"""بوابة التراخيص: كل تبعيات المشروع لها قرار مسجَّل.

قاعدة المشروع: **نقبل الكود، نرفض الترخيص**. التبعية غير المسجَّلة تُرفض
حتى لو كانت مشهورة، والتبعية المرفوضة تُرفض حتى لو كانت مفيدة.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from maestro.provenance.registry import ProvenanceRegistry  # noqa: E402

REGISTRY_PATH = ROOT / "docs" / "provenance" / "dependencies.json"


def _requirement_name(requirement: str) -> str:
    """اسم التبععية من متطلّب PEP 508."""
    match = re.match(r"^\s*([A-Za-z0-9._-]+)", requirement)
    return match.group(1) if match else requirement.strip()


def declared_dependencies() -> list[str]:
    """كل تبعيات المشروع: أساسية وأخرى اختيارية."""
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project", {})
    names = [_requirement_name(req) for req in project.get("dependencies", [])]
    for group in project.get("optional-dependencies", {}).values():
        names.extend(_requirement_name(req) for req in group)
    return names


def main() -> int:
    """يقارن المعلن بالسجل ويعيد قائمة المشاكل."""
    if not REGISTRY_PATH.is_file():
        print(f"FAIL: سجل التبعيات مفقود: {REGISTRY_PATH}")
        return 1
    registry = ProvenanceRegistry.load(REGISTRY_PATH)
    declared = declared_dependencies()
    problems = registry.check(declared)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1
    print(f"سيرى الترخيص: {len(declared)} تبعية مصرّح بها.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
