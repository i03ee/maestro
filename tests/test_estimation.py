"""اختبارات تقدير التكلفة: قبل الإنفاق، ولا صفر صامت."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from maestro.estimation.cost import (
    estimate_cost,
    estimate_from_document,
    worst_case_cost,
)
from maestro.routing.base import ModelProfile
from maestro.routing.deepseek import deepseek_fallback_profile, deepseek_flash_profile
from maestro.routing.local import local_profile

ROOT = Path(__file__).resolve().parent.parent


class TestEstimate(unittest.TestCase):
    """الحساب نفسه."""

    def setUp(self) -> None:
        self.profiles = {
            "local": local_profile(),
            "api": deepseek_flash_profile(off_peak=True),
            "fallback": deepseek_fallback_profile(),
        }

    def test_local_costs_nothing(self) -> None:
        estimate = estimate_cost(
            capability_name="media.render",
            max_tokens=1000,
            profiles_by_tier=self.profiles,
            ensemble=("local",),
        )
        self.assertEqual(estimate.max_cost_usd, 0.0)
        self.assertTrue(estimate.complete)

    def test_worst_case_sums_the_whole_chain(self) -> None:
        estimate = estimate_cost(
            capability_name="media.render",
            max_tokens=10_000,
            profiles_by_tier=self.profiles,
            ensemble=("local", "api", "fallback"),
        )
        expected = sum(
            profile.estimate_cost(10_000, 10_000) for profile in self.profiles.values()
        )
        self.assertAlmostEqual(estimate.max_cost_usd, expected)
        self.assertEqual(len(estimate.per_model_cost_usd), 3)

    def test_unpriced_model_is_not_counted_as_zero(self) -> None:
        estimate = estimate_cost(
            capability_name="media.render",
            max_tokens=1000,
            profiles_by_tier={"api": self.profiles["api"]},
            ensemble=("local", "api"),
        )
        self.assertFalse(estimate.complete)
        self.assertEqual(estimate.unpriced_models, ("local",))

    def test_estimate_from_document_reads_budget_and_ensemble(self) -> None:
        document = json.loads(
            (ROOT / "src" / "maestro" / "evals" / "golden" / "case_catalog_ingest.json").read_text(
                encoding="utf-8"
            )
        )
        estimate = estimate_from_document(document, profiles_by_tier=self.profiles)
        self.assertEqual(estimate.capability, "catalog.ingest")
        self.assertEqual(estimate.max_tokens, 8000)
        self.assertTrue(estimate.complete)

    def test_estimate_from_catalogue_capability(self) -> None:
        from maestro.company.catalogue import capability_by_name

        capability = capability_by_name("commercial.pricing")
        estimate = worst_case_cost(
            capability, max_tokens=20_000, profiles_by_tier=self.profiles
        )
        self.assertTrue(estimate.complete)
        self.assertGreater(estimate.max_cost_usd, 0.0)

    def test_estimate_is_deterministic(self) -> None:
        first = estimate_cost(
            capability_name="media.render",
            max_tokens=5000,
            profiles_by_tier=self.profiles,
            ensemble=("api", "local"),
        )
        second = estimate_cost(
            capability_name="media.render",
            max_tokens=5000,
            profiles_by_tier=self.profiles,
            ensemble=("api", "local"),
        )
        self.assertEqual(first.as_dict(), second.as_dict())


class TestEstimateCommand(unittest.TestCase):
    """الأمر من الطرفية."""

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "maestro", "estimate", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
        )

    def test_estimate_prints_a_number(self) -> None:
        result = self._run(
            "--ir", "src/maestro/evals/golden/case_catalog_ingest.json"
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout[result.stdout.index("{") : result.stdout.rindex("}") + 1])
        self.assertGreater(payload["max_cost_usd"], 0.0)
        self.assertTrue(payload["complete"])

    def test_ceiling_is_enforced(self) -> None:
        result = self._run(
            "--ir",
            "src/maestro/evals/golden/case_catalog_ingest.json",
            "--max-cost-usd",
            "0.000001",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("رُفض", result.stdout)


if __name__ == "__main__":
    unittest.main()
