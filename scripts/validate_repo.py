#!/usr/bin/env python3
"""بوابة ثوابت المستودع — تعمل محلياً بلا شبكة وبلا أي تسامح.

كل فحص ثنائي: إمّا يمرّ وإمّا يفشل. لا توجد نسب خطأ، ولا عتبات تسامح،
ولا إعادة محاولة تُخفي الفشل. هذا هو الفحص الذي يُبنى عليه كل شيء آخر.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

REQUIRED_FILES: tuple[str, ...] = (
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "CONTRIBUTING.md",
    "pyproject.toml",
    "docs/ARCHITECTURE.md",
    "docs/SECURITY.md",
    "docs/PROTOCOL.md",
    "docs/provenance/dependencies.json",
    "docs/provenance/REGISTRY.md",
    "scripts/validate_repo.py",
    "scripts/check_licenses.py",
    "src/maestro/__init__.py",
    "src/maestro/ir/rules.py",
    "src/maestro/ir/validate.py",
    "src/maestro/routing/router.py",
    "src/maestro/guards/budget.py",
    "src/maestro/guards/permission.py",
    "src/maestro/baseline/recorder.py",
    "src/maestro/evidence/log.py",
    "src/maestro/provenance/registry.py",
    "src/maestro/company/catalogue.py",
    "src/maestro/company/topology.py",
    "src/maestro/company/registry.py",
    "docs/CAPABILITY_CATALOGUE.md",
    "docs/AC_EVIDENCE.md",
    "scripts/catalogue_report.py",
    "scripts/verify_acceptance.py",
    "examples/plugin_minimal/minimal_provider.py",
    "src/maestro/producers/idea.py",
    "src/maestro/producers/research.py",
    "src/maestro/producers/structured.py",
    "src/maestro/company/contracts.py",
    "scripts/contracts_report.py",
    "docs/CAPABILITY_CONTRACTS.json",
    "src/maestro/doctor/check.py",
    "src/maestro/estimation/cost.py",
    "src/maestro/routing/local.py",
    "src/maestro/evals/cases.py",
    "src/maestro/evals/runner.py",
    "docs/RUNBOOK.md",
    "docs/DELIVERY_PACK.md",
    "scripts/eval_check.py",
    "scripts/load_check.py",
    "scripts/build_delivery_pack.py",
    ".github/workflows/ci.yml",
)

TEXT_SUFFIXES = {".py", ".md", ".json", ".toml", ".yml", ".yaml", ".txt", ".sh", ".mjs", ".js", ".css"}

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("مفتاح سري", re.compile(r"sk-[A-Za-z0-9]{16,}")),
    ("رمز GitHub", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("مفتاح خاص", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("كلمة مرور", re.compile(r"(?i)(password|passwd|secret|api[_-]?key)\s*[:=]\s*['\"]?[^\s'\"]{8,}")),
    ("رمز وصول", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
)

#: محارف صينية/كورية/يابانية لا مكان لها في مستودع عربي-إنجليزي.
CJK_PATTERN = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")

MAX_TEXT_FILE_BYTES = 1_000_000

#: عيّنة ذهبية واحدة تحتوي قيمة مفتعلة عمداً لاختبار كشف الأسرار (IR-14).
#: القائمة مقيّدة بهذا المسار بالضبط؛ توسيعها يعني تعطيل البوابة.
SECRET_SCAN_ALLOWLIST: frozenset[str] = frozenset({"tests/golden/ir_invalid_examples.json"})


def _fail(message: str) -> None:
    print(f"FAIL: {message}")
    globals()["FAILURES"].append(message)


FAILURES: list[str] = []


def check_required_files() -> None:
    """كل ملف أساسي موجود فعلاً."""
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            _fail(f"ملف مفقود: {relative}")


def _iter_text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".git", "node_modules", "__pycache__", ".venv", "venv"} for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            files.append(path)
    return files


def check_no_secrets() -> None:
    """لا أسرار في أي ملف نصّي."""
    for path in _iter_text_files():
        if path.relative_to(ROOT).as_posix() in SECRET_SCAN_ALLOWLIST:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(content):
                _fail(f"يشبه {label} في {path.relative_to(ROOT)}")


def check_no_cjk() -> None:
    """لا محارف صينية/كورية مسرّبة إلى النص."""
    for path in _iter_text_files():
        content = path.read_text(encoding="utf-8", errors="ignore")
        match = CJK_PATTERN.search(content)
        if match:
            _fail(f"محرف مسرّب في {path.relative_to(ROOT)}: {match.group(0)!r}")


def check_python_compiles() -> None:
    """كل ملفات بايثون تُصرَّف بلا خطأ."""
    result = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "src", "scripts", "tests"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        _fail(f"فشل تصريف بايثون:\n{result.stdout}{result.stderr}")


def check_file_sizes() -> None:
    """لا ملف نصّي ضخم في المستودع."""
    for path in _iter_text_files():
        size = path.stat().st_size
        if size > MAX_TEXT_FILE_BYTES:
            _fail(f"ملف نصّي كبير: {path.relative_to(ROOT)} ({size} بايت)")


def check_ci_is_strict() -> None:
    """خطّ الأنابيب لا يتسامح مع الفشل ولا يسمح بالفحص الاختياري."""
    workflow = ROOT / ".github" / "workflows" / "ci.yml"
    if not workflow.is_file():
        _fail("ملف خط الأنابيب مفقود: .github/workflows/ci.yml")
        return
    content = workflow.read_text(encoding="utf-8")
    for forbidden in ("continue-on-error", "|| true", "fail-fast: false"):
        if forbidden in content:
            _fail(f"خط الأنابيب يحتوي تساهلاً ممنوعاً: {forbidden}")


def check_protocol_declares_no_error_rates() -> None:
    """بروتوكول التنفيذ يعلن صراحةً رفض نسب الخطأ."""
    protocol = ROOT / "docs" / "PROTOCOL.md"
    if not protocol.is_file():
        return
    content = protocol.read_text(encoding="utf-8")
    if "بلا نسب" not in content and "لا نسب" not in content:
        _fail("docs/PROTOCOL.md لا يعلن قاعدة «بلا نسب خطأ» صراحةً.")


def check_company_catalogue() -> None:
    """كتالوج الشركة متّسق، والوثيقة المولَّدة مطابقة للشيفرة."""
    try:
        from maestro.company.topology import check_catalogue
    except ImportError as error:  # pragma: no cover
        _fail(f"تعذّر استيراد كتالوج الشركة: {error}")
        return
    problems = check_catalogue()
    for problem in problems:
        _fail(f"كتالوج الشركة: {problem}")
    result = subprocess.run(
        [sys.executable, "scripts/catalogue_report.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        _fail(f"وثيقة الكتالوج انحرفت عن الشيفرة:\n{result.stdout}{result.stderr}")


def check_capability_contracts() -> None:
    """عقود القدرات مبنيّة من الكتالوج، ومطابقة له، وقابلة للتنفيذ."""
    result = subprocess.run(
        [sys.executable, "scripts/contracts_report.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        _fail(f"عقود القدرات:\n{result.stdout}{result.stderr}")


def check_acceptance_evidence() -> None:
    """وثيقة الدليل مطابقة للشيفرة (والشواهد تُشغَّل في خط الأنابيب)."""
    result = subprocess.run(
        [sys.executable, "scripts/verify_acceptance.py", "--check-docs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        _fail(f"وثيقة القبول انحرفت عن الشيفرة:\n{result.stdout}{result.stderr}")


def main() -> int:
    """يشغّل كل الفحوص ويعيد رمز الخروج."""
    checks = (
        check_required_files,
        check_no_secrets,
        check_no_cjk,
        check_python_compiles,
        check_file_sizes,
        check_ci_is_strict,
        check_protocol_declares_no_error_rates,
        check_company_catalogue,
        check_capability_contracts,
        check_acceptance_evidence,
    )
    for check in checks:
        check()
    if FAILURES:
        print(f"\nفشل التحقق: {len(FAILURES)} مشكلة.")
        return 1
    print(
        f"سيرى التحقق: {len(REQUIRED_FILES)} ملفاً أساسياً، لا أسرار، لا محارف مسرّبة، "
        "كود يصرَّف، وكتالوج الشركة متّسق."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
