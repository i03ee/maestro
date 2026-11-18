"""اختبار ثوابت المستودع: البوابتان يجب أن تمرّا في كل طلب."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestRepositoryInvariants(unittest.TestCase):
    """البوابات نفسها تخضع للاختبار."""

    def test_validate_repo_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_repo.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_check_licenses_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/check_licenses.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_ci_workflow_has_no_tolerance_switches(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        for forbidden in ("continue-on-error", "|| true", "fail-fast: false"):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, workflow)

    def test_protocol_forbids_error_rates(self) -> None:
        protocol = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
        self.assertIn("بلا نسب", protocol)


if __name__ == "__main__":
    unittest.main()
