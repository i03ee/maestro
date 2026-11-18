"""اختبارات فحص البيئة: حكم واضح لكل بند، ولا أسرار في التقرير."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from maestro.doctor.check import DoctorCheck, DoctorReport, run_doctor

ROOT = Path(__file__).resolve().parent.parent


class TestDoctorReport(unittest.TestCase):
    """منطق التقرير."""

    def test_required_failure_makes_the_report_fail(self) -> None:
        report = DoctorReport(
            checks=(
                DoctorCheck("س", required=True, ok=False, detail_ar="تعذّر"),
                DoctorCheck("ص", required=False, ok=False, detail_ar="غائب"),
            )
        )
        self.assertFalse(report.ok)
        self.assertEqual(len(report.failed_required), 1)

    def test_optional_failure_does_not_fail_the_report(self) -> None:
        report = DoctorReport(
            checks=(
                DoctorCheck("س", required=True, ok=True, detail_ar="تمام"),
                DoctorCheck("ص", required=False, ok=False, detail_ar="غائب"),
            )
        )
        self.assertTrue(report.ok)
        self.assertEqual(report.failed_required, ())

    def test_report_is_serialisable(self) -> None:
        payload = DoctorReport(checks=()).as_dict()
        self.assertIn("checks", payload)
        json.dumps(payload)


class TestDoctorChecks(unittest.TestCase):
    """بنود الفحص نفسها."""

    def test_every_check_has_a_detail(self) -> None:
        report = run_doctor()
        self.assertGreaterEqual(len(report.checks), 5)
        for check in report.checks:
            with self.subTest(check=check.name):
                self.assertTrue(check.detail_ar.strip())

    def test_python_is_always_satisfied_here(self) -> None:
        report = run_doctor()
        python_check = next(check for check in report.checks if check.name == "بايثون")
        self.assertTrue(python_check.ok)
        self.assertTrue(python_check.required)

    def test_report_never_prints_the_key_value(self) -> None:
        report = run_doctor()
        key_value = os.environ.get("DEEPSEEK_API_KEY")
        if not key_value:
            self.skipTest("لا مفتاح في البيئة")
        payload = json.dumps(report.as_dict(), ensure_ascii=False)
        self.assertNotIn(key_value, payload)

    def test_key_presence_is_reported_without_its_value(self) -> None:
        report = run_doctor()
        key_check = next(check for check in report.checks if check.name == "مفتاح المزوّد")
        self.assertIn("DEEPSEEK_API_KEY", key_check.detail_ar)


class TestDoctorCommand(unittest.TestCase):
    """الأمر من الطرفية."""

    def test_command_runs_and_prints_checks(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "maestro", "doctor"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        )
        self.assertIn(result.returncode, (0, 1))
        self.assertIn("البيئة", result.stdout)


if __name__ == "__main__":
    unittest.main()
