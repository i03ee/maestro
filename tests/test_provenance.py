"""اختبارات سجل التراخيص: كل تبعية لها قرار."""

from __future__ import annotations

import unittest
from pathlib import Path

from maestro.provenance.registry import ProvenanceRegistry

REGISTRY = Path(__file__).resolve().parent.parent / "docs" / "provenance" / "dependencies.json"


class TestProvenanceRegistry(unittest.TestCase):
    """نقبل الكود، نرفض الترخيص."""

    def setUp(self) -> None:
        self.registry = ProvenanceRegistry.load(REGISTRY)

    def test_allowed_dependency_passes(self) -> None:
        self.assertEqual(self.registry.check(["pydantic-ai-slim"]), [])

    def test_unknown_dependency_is_rejected(self) -> None:
        problems = self.registry.check(["requests"])
        self.assertEqual(len(problems), 1)
        self.assertIn("requests", problems[0])

    def test_denied_dependency_is_rejected(self) -> None:
        problems = self.registry.check(["k6"])
        self.assertEqual(len(problems), 1)
        self.assertIn("k6", problems[0])

    def test_denied_entries_keep_their_reason(self) -> None:
        entry = self.registry.decision_for("mobSF")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.decision, "deny")
        self.assertTrue(entry.rationale_ar.strip())

    def test_every_entry_has_license_and_source(self) -> None:
        for entry in self.registry.entries:
            with self.subTest(name=entry.name):
                self.assertTrue(entry.license.strip())
                self.assertTrue(entry.source.strip())
                self.assertIn(entry.decision, {"allow", "deny"})


if __name__ == "__main__":
    unittest.main()
