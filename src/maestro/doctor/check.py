"""فحص البيئة قبل التشغيل.

لماذا؟ لأن أكثر أخطاء التشغيل لا تأتي من الشيفرة بل من **البيئة**: بايثون
قديم، حزمة اختيارية غير مثبّتة، مفتاح غائب، مجلد كتابة غير قابل للكتابة.
وفحصُها متقدّم لا متأخر: كل بند يُذكر بحكمه (مطلوب / اختياري) وبنتيجته.

**لا يُطبع أي سرّ**: يُذكر وجود المفتاح واسم متغيّره فقط.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

MINIMUM_PYTHON = (3, 11)


@dataclass(frozen=True)
class DoctorCheck:
    """بند فحص واحد."""

    name: str
    required: bool
    ok: bool
    detail_ar: str

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "required": self.required,
            "ok": self.ok,
            "detail_ar": self.detail_ar,
        }


@dataclass(frozen=True)
class DoctorReport:
    """تقرير الفحص."""

    checks: tuple[DoctorCheck, ...]

    @property
    def failed_required(self) -> tuple[DoctorCheck, ...]:
        """البنود المطلوبة التي فشلت."""
        return tuple(check for check in self.checks if check.required and not check.ok)

    @property
    def ok(self) -> bool:
        return not self.failed_required

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "checks": [check.as_dict() for check in self.checks],
        }


def _check_python() -> DoctorCheck:
    version = sys.version_info
    ok = version[:2] >= MINIMUM_PYTHON
    return DoctorCheck(
        name="بايثون",
        required=True,
        ok=ok,
        detail_ar=f"{version.major}.{version.minor}.{version.micro}",
    )


def _check_git() -> DoctorCheck:
    executable = shutil.which("git")
    if executable is None:
        return DoctorCheck("git", required=False, ok=False, detail_ar="غير مثبّت")
    try:
        result = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError) as error:
        return DoctorCheck("git", required=False, ok=False, detail_ar=f"تعذّر التشغيل: {error}")
    return DoctorCheck("git", required=False, ok=True, detail_ar=result.stdout.strip())


def _check_agent_layer() -> DoctorCheck:
    available = importlib.util.find_spec("pydantic_ai") is not None
    return DoctorCheck(
        name="طبقة الوكلاء",
        required=False,
        ok=available,
        detail_ar=(
            "مثبّتة" if available else "غير مثبّتة — ثبّت: pip install -e '.[agent]'"
        ),
    )


def _check_api_key() -> DoctorCheck:
    variable = "DEEPSEEK_API_KEY"
    present = bool(os.environ.get(variable))
    return DoctorCheck(
        name="مفتاح المزوّد",
        required=False,
        ok=present,
        detail_ar=(
            f"مضبوط ({variable})"
            if present
            else f"غير مضبوط ({variable}) — التشغيل الحيّ معطّل، والباقي يعمل"
        ),
    )


def _check_writable() -> DoctorCheck:
    try:
        with tempfile.NamedTemporaryFile(dir=Path.cwd(), prefix=".doctor-", delete=True):
            pass
    except OSError as error:
        return DoctorCheck("قابلة للكتابة", required=True, ok=False, detail_ar=str(error))
    return DoctorCheck("قابلة للكتابة", required=True, ok=True, detail_ar="نعم")


def _check_local_model() -> DoctorCheck:
    """هل يوجد خادم محلي متوافق مع OpenAI؟ (اختياري)

    لا يُعدّ غيابُه فشلاً: المشروع يعمل بلا نموذج محلي. لكن **يُذكر**
    صراحةً حتى لا يُظنّ أن الطبقة المحلية موجودة وهي ليست.
    """
    import urllib.error
    import urllib.request

    from ..routing.local import DEFAULT_LOCAL_BASE_URL

    base_url = os.environ.get("MAESTRO_LOCAL_BASE_URL", DEFAULT_LOCAL_BASE_URL)
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/models", timeout=2) as response:
            payload = response.read().decode("utf-8")
    except (urllib.error.URLError, OSError, ValueError):
        return DoctorCheck(
            name="النموذج المحلي",
            required=False,
            ok=False,
            detail_ar=f"لا خادم محلي على {base_url} — الطبقة المحلية غير متاحة",
        )
    models = 0
    try:
        import json

        models = len(json.loads(payload).get("data", []))
    except Exception:  # noqa: BLE001 — الردّ غريب لا يمنع الفحص
        models = 0
    return DoctorCheck(
        name="النموذج المحلي",
        required=False,
        ok=models > 0,
        detail_ar=f"متاح على {base_url} — {models} نموذجاً",
    )


def _check_gates() -> DoctorCheck:
    script = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "validate_repo.py"
    if not script.is_file():
        return DoctorCheck("بوابات المستودع", required=False, ok=False, detail_ar="الملف غير موجود")
    result = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, timeout=180
    )
    ok = result.returncode == 0
    detail = "تمرّ" if ok else (result.stdout.strip().splitlines() or ["فشلت"])[-1]
    return DoctorCheck("بوابات المستودع", required=False, ok=ok, detail_ar=detail)


def run_doctor() -> DoctorReport:
    """يشغّل كل بنود الفحص."""
    checks = (
        _check_python(),
        _check_writable(),
        _check_git(),
        _check_agent_layer(),
        _check_api_key(),
        _check_local_model(),
        _check_gates(),
    )
    return DoctorReport(checks=checks)
