"""اختبارات أمر «كل البوابات»: ترتيب ثابت، وبوابات حقيقية."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

if os.environ.get("MAESTRO_ACCEPTANCE_CHILD") == "1":
    raise unittest.SkipTest("عملية فرعية لجمع نتائج الاختبارات")

ROOT = Path(__file__).resolve().parent.parent


def _load_module():
    """يحمّل سكربت verify_all كوحدة ( Scripts ليست حزمة)."""
    path = ROOT / "scripts" / "verify_all.py"
    spec = importlib.util.spec_from_file_location("verify_all", path)
    module = importlib.util.module_from_spec(spec)
    # لا بد من تسجيل الوحدة قبل التنفيذ: dataclasses يحتاجها في sys.modules
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestGateList(unittest.TestCase):
    """قائمة البوابات."""

    def setUp(self) -> None:
        self.module = _load_module()

    def test_gates_are_declared_in_a_fixed_order(self) -> None:
        names = [gate.name for gate in self.module.GATES]
        self.assertEqual(names[0], "ثوابت المستودع")
        self.assertEqual(names[1], "التراخيص")
        self.assertIn("شواهد القبول", names)
        self.assertIn("مقياس الحمل", names)

    def test_every_gate_script_exists(self) -> None:
        for gate in self.module.GATES:
            script = gate.command[1]
            with self.subTest(gate=gate.name):
                self.assertTrue((ROOT / script).is_file(), msg=script)

    def test_gates_are_unique(self) -> None:
        names = [gate.name for gate in self.module.GATES]
        self.assertEqual(len(set(names)), len(names))


class TestVerifyAllCommand(unittest.TestCase):
    """الأمر من الطرفية."""

    def test_fast_gates_pass_and_report_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "verify_all.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/verify_all.py",
                    "--only",
                    "ثوابت المستودع,التراخيص",
                    "--json",
                    str(report_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                # العملية الفرعية تتخطّى الاختبارات الثقيلة: شواهد القبول
                # تشغّل المجموعة، والمجموعة تشغّل هذا الاختبار — فبلا هذا
                # الحاجز ندخل في تداخل لا ينتهي.
                env={**os.environ, "MAESTRO_ACCEPTANCE_CHILD": "1"},
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["failed"], 0)
            self.assertEqual(len(payload["gates"]), 2)
            for gate in payload["gates"]:
                with self.subTest(gate=gate["gate"]):
                    self.assertTrue(gate["ok"])
                    self.assertIn("last_line", gate)


if __name__ == "__main__":
    unittest.main()
