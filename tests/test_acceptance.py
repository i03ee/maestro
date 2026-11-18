"""اختبارات حزمة القبول: الشواهد نفسها، ونقطة الحقن.

في العملية الفرعية التي تشغّلها الشواهد لجمع نتائج الاختبارات، يتخطّى هذا
الوحدة نفسها — تفادياً للتداخل الذي لا ينتهي.
"""

from __future__ import annotations

import os
import unittest

if os.environ.get("MAESTRO_ACCEPTANCE_CHILD") == "1":
    raise unittest.SkipTest("عملية فرعية لجمع نتائج الاختبارات")

from maestro.acceptance.criteria import (  # noqa: E402
    CRITERIA,
    CRITERIA_BY_ID,
    implemented_criteria,
    pending_criteria,
)
from maestro.acceptance.proofs import PROOFS, ProofResult  # noqa: E402
from maestro.acceptance.rebuild import compute_rebuild_hash  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestCriteriaTable(unittest.TestCase):
    """جدول المعايير نفسه."""

    def test_twenty_criteria_with_unique_ids(self) -> None:
        self.assertEqual(len(CRITERIA), 20)
        self.assertEqual(len(CRITERIA_BY_ID), 20)

    def test_ids_follow_the_ac_numbering(self) -> None:
        self.assertEqual(
            [criterion.id for criterion in CRITERIA],
            [f"AC-{index:02d}" for index in range(1, 21)],
        )

    def test_every_criterion_has_an_artefact(self) -> None:
        for criterion in CRITERIA:
            with self.subTest(criterion=criterion.id):
                self.assertTrue(criterion.artefact.strip())

    def test_unproven_criteria_state_the_missing_piece(self) -> None:
        for criterion in pending_criteria():
            with self.subTest(criterion=criterion.id):
                self.assertTrue(criterion.not_proven_reason_ar.strip())

    def test_implemented_criteria_point_to_a_real_proof(self) -> None:
        for criterion in implemented_criteria():
            with self.subTest(criterion=criterion.id):
                self.assertIn(criterion.proof_key, PROOFS)


class TestProofs(unittest.TestCase):
    """كل شاهد منفَّذ يمرّ."""

    def test_every_proof_passes(self) -> None:
        for key, proof in sorted(PROOFS.items()):
            with self.subTest(proof=key):
                result = proof()
                self.assertIsInstance(result, ProofResult)
                self.assertTrue(result.ok, msg=f"{key}: {result.detail_ar}")


class TestInjectionTest(unittest.TestCase):
    """اختبار الحقن: الأهمّ في هذه الحزمة.

    نسأل: هل يكتشف المفتّش عيباً حقيقياً؟ فنحقن عيباً (حذف فحص الصلاحية)
    في نسخة من الشيفرة، ونطالب بأن تقبله النسخة المعطوبة وأن ترفضها الأصلية.
    """

    def test_defect_changes_behaviour_and_is_observable(self) -> None:
        from maestro.acceptance.proofs import injected_defect_is_detected

        result = injected_defect_is_detected()
        self.assertTrue(result.ok, msg=result.detail_ar)
        self.assertIn("مرصود", result.detail_ar)


class TestRebuildHash(unittest.TestCase):
    """بصمة إعادة البناء."""

    def test_hash_is_stable(self) -> None:
        first = compute_rebuild_hash(ROOT)
        second = compute_rebuild_hash(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_hash_changes_when_a_file_changes(self) -> None:
        import tempfile
        import shutil
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "tree"
            shutil.copytree(Path(ROOT) / "src", copy / "src")
            before = compute_rebuild_hash(copy)
            target = copy / "src" / "maestro" / "version.py"
            target.write_text(
                target.read_text(encoding="utf-8") + "\n# تغيير\n", encoding="utf-8"
            )
            after = compute_rebuild_hash(copy)
            self.assertNotEqual(before, after)


class TestEvidenceDocument(unittest.TestCase):
    """وثيقة الدليل لا تنحرف عن الشيفرة."""

    def test_document_matches_criteria(self) -> None:
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "scripts/verify_acceptance.py", "--check-docs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
