#!/usr/bin/env python3
"""تجميع حزمة التسليم: الشيفرة + الأدلة + الوثائق + البصمات.

    python3 scripts/build_delivery_pack.py --out dist/

الحزمة ZIP واحدة تضم:
- الشيفرة كما هي (بلا .git).
- تقرير البوابات (ثوابت المستودع، التراخيص، الكتالوج، القبول).
- تقرير التقييم ومقياس الحمل.
- بصمة إعادة البناء وبصمة كل ملف.
- ملخّص (manifest.json) يربط كل artefact بما يثبته.

حزمة التسليم هي ما يُسلَّم للمراجع: لا «شجرة نظيف» ولا لقطات شاشة.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from maestro.acceptance.rebuild import compute_rebuild_hash  # noqa: E402

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist"}


def _run(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr)


def _collect_reports(out_dir: Path) -> list[tuple[str, str]]:
    """يشغّل الفحوص ويكتب تقاريرها."""
    reports: list[tuple[str, str]] = []
    checks = [
        ("gates", [sys.executable, "scripts/validate_repo.py"]),
        ("licenses", [sys.executable, "scripts/check_licenses.py"]),
        ("catalogue", [sys.executable, "scripts/catalogue_report.py", "--check"]),
        ("acceptance", [sys.executable, "scripts/verify_acceptance.py"]),
        ("evals", [sys.executable, "scripts/eval_check.py"]),
        ("load", [sys.executable, "scripts/load_check.py", "--requests", "80", "--concurrency", "16"]),
    ]
    for name, command in checks:
        code, output = _run(command)
        path = out_dir / "reports" / f"{name}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"$ {' '.join(command)}\n\n{output}\n", encoding="utf-8")
        reports.append((name, str(path.relative_to(out_dir))))
    return reports


def main() -> int:
    """يبني الحزمة."""
    parser = argparse.ArgumentParser(description="تجميع حزمة التسليم.")
    parser.add_argument("--out", default="dist", help="مجلد الإخراج")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    reports = _collect_reports(out_dir)

    manifest = {
        "project": "MAESTRO",
        "rebuild_hash": compute_rebuild_hash(ROOT),
        "reports": {name: path for name, path in reports},
        "contents": [
            "src/ — نواة الشركة",
            "tests/ — الاختبارات والعقود الذهبية",
            "docs/ — القرارات والبروتوكول وكتالوج الشركة ودليل القبول",
            "reports/ — مخرجات كل بوابة عند البناء",
            "manifest.json — هذا الملف",
        ],
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    archive = out_dir.parent / f"maestro-delivery-{manifest['rebuild_hash'][:12]}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(out_dir.rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(out_dir))
        for relative in ("src", "tests", "docs", "scripts", "examples", "pyproject.toml",
                         "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md"):
            source = ROOT / relative
            if source.is_file():
                bundle.write(source, Path("source") / relative)
            elif source.is_dir():
                for path in sorted(source.rglob("*")):
                    if path.is_file() and not any(part in SKIP_DIRS for part in path.parts):
                        bundle.write(path, Path("source") / path.relative_to(ROOT))

    print(f"بصمة إعادة البناء: {manifest['rebuild_hash']}")
    print(f"الحزمة: {archive} ({archive.stat().st_size} بايت)")
    print(f"تقارير: {len(reports)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
