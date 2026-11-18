"""اختبارات طبقة التشغيل: قدرة واحدة عبر كل البوابات."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from maestro.evidence.log import EvidenceLog
from maestro.guards.budget import BudgetGuard
from maestro.guards.permission import PermissionGuard
from maestro.routing.base import CompletionResponse, ModelProfile, RoutingPolicy
from maestro.routing.offline import ScriptedProvider
from maestro.routing.router import ModelRouter
from maestro.runtime.registry import CapabilityRegistry
from maestro.runtime.runner import CapabilityRunner
from maestro.runtime.spec import CapabilitySpec

GOLDEN = Path(__file__).parent / "golden"

PROFILE = ModelProfile(
    name="local",
    tier="local",
    model="test-model",
    cost_in_per_mtok=0.0,
    cost_out_per_mtok=0.0,
    max_context=8192,
)


def _doc(name: str) -> dict:
    return json.loads((GOLDEN / name).read_text(encoding="utf-8"))


def _response(text: str = "نتيجة") -> CompletionResponse:
    return CompletionResponse(text=text, tokens_in=10, tokens_out=5, model="test-model")


class RuntimeCase(unittest.TestCase):
    """أدوات بناء متاحة لكل اختبارات هذه الطبقة."""

    def setUp(self) -> None:
        self.registry = CapabilityRegistry()
        self.registry.register(
            CapabilitySpec(
                name="media.render",
                description_ar="توليد صورة بطاقة عرض",
                required_tools=("render.image",),
                default_authority=1,
            )
        )
        self.registry.register(
            CapabilitySpec(
                name="catalog.ingest",
                description_ar="تحويل ملف مورّد إلى منتجات",
                required_tools=("saleor.graphql",),
                default_authority=2,
                critical=True,
            )
        )
        self.permissions = PermissionGuard(
            allowed_capabilities=frozenset({"media.render", "catalog.ingest"}),
            max_authority=2,
        )
        self.provider = ScriptedProvider("local", [_response()])
        self.router = ModelRouter(
            providers={"local": self.provider},
            profiles={"local": PROFILE},
            policy=RoutingPolicy(),
            budget=BudgetGuard(max_cost_usd=1.0, max_tokens=100_000),
        )

    def _runner(self, evidence: EvidenceLog | None = None) -> CapabilityRunner:
        return CapabilityRunner(self.registry, self.router, self.permissions, evidence)


class TestRegistry(RuntimeCase):
    """سجل القدرات."""

    def test_registered_capability_is_found(self) -> None:
        self.assertIsNotNone(self.registry.get("media.render"))

    def test_unknown_capability_is_absent(self) -> None:
        self.assertIsNone(self.registry.get("payment.capture"))

    def test_critical_capabilities_are_listed(self) -> None:
        self.assertEqual(self.registry.critical_names(), ("catalog.ingest",))


class TestRunnerStages(RuntimeCase):
    """كل بوابة تُوقف المسار عند رفضها."""

    def test_invalid_ir_stops_at_first_stage(self) -> None:
        doc = _doc("ir_valid_minimal.json")
        doc["ir_version"] = "0.9"
        report = self._runner().run(doc)
        self.assertFalse(report.ok)
        self.assertEqual(report.stage, "ir")
        self.assertEqual(report.findings[0].rule_id, "IR-01")
        self.assertEqual(self.provider.calls, [])

    def test_unknown_capability_stops_at_registry(self) -> None:
        doc = _doc("ir_valid_minimal.json")
        doc["capability"] = "billing.quote"
        report = self._runner().run(doc)
        self.assertFalse(report.ok)
        self.assertEqual(report.stage, "registry")

    def test_permission_denied_stops_before_model(self) -> None:
        """سقف صلاحية أدنى من مستوى المهمة يُرفض عند بوابة الصلاحيات."""
        doc = _doc("ir_valid_minimal.json")
        doc["authority"] = 2
        runner = CapabilityRunner(
            self.registry,
            self.router,
            PermissionGuard(
                allowed_capabilities=frozenset({"media.render", "catalog.ingest"}),
                max_authority=1,
            ),
        )
        report = runner.run(doc)
        self.assertFalse(report.ok)
        self.assertEqual(report.stage, "permission")
        self.assertEqual(self.provider.calls, [])

    def test_budget_ceiling_stops_before_model(self) -> None:
        doc = _doc("ir_valid_minimal.json")
        doc["budget"]["max_tokens"] = 12000
        doc["budget"]["max_cost_usd"] = 0.5
        runner = CapabilityRunner(
            self.registry,
            self.router,
            self.permissions,
        )
        report = runner.run(doc)
        self.assertTrue(report.ok)
        self.assertEqual(report.stage, "done")

    def test_budget_overrun_is_reported_not_hidden(self) -> None:
        doc = _doc("ir_valid_minimal.json")
        doc["budget"]["max_cost_usd"] = 0.5
        doc["budget"]["max_tokens"] = 12000
        provider = ScriptedProvider("local", [_response()])
        router = ModelRouter(
            providers={"local": provider},
            profiles={"local": PROFILE},
            policy=RoutingPolicy(),
            budget=BudgetGuard(max_cost_usd=1.0, max_tokens=100_000),
        )
        runner = CapabilityRunner(self.registry, router, self.permissions)
        doc["budget"]["max_output_tokens"] = 10_000_000
        report = runner.run(doc)
        self.assertFalse(report.ok)
        self.assertEqual(report.stage, "budget")

    def test_successful_run_reaches_done(self) -> None:
        doc = _doc("ir_valid_minimal.json")
        report = self._runner().run(doc)
        self.assertTrue(report.ok)
        self.assertEqual(report.stage, "done")
        self.assertEqual(report.output, "نتيجة")
        self.assertEqual(len(report.attempts), 1)


class TestEvidence(RuntimeCase):
    """كل تنفيذ ناجح يترك دليلاً."""

    def test_successful_run_appends_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = EvidenceLog(Path(tmp) / "evidence.jsonl")
            doc = _doc("ir_valid_minimal.json")
            report = self._runner(log).run(doc)
            self.assertTrue(report.ok)
            self.assertIsNotNone(report.evidence_hash)
            entries = log.entries()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].kind, "capability")
            self.assertTrue(log.verify())

    def test_rejected_run_leaves_no_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = EvidenceLog(Path(tmp) / "evidence.jsonl")
            doc = _doc("ir_valid_minimal.json")
            doc["ir_version"] = "0.9"
            report = self._runner(log).run(doc)
            self.assertFalse(report.ok)
            self.assertEqual(log.entries(), [])


class TestCriticalCapability(RuntimeCase):
    """القدرة الحرجة تُنفَّذ مقيَّدة بدليل وتكرار معلن."""

    def test_critical_capability_requires_agreement_and_evidence(self) -> None:
        doc = _doc("ir_valid_critical.json")
        report = self._runner().run(doc)
        self.assertTrue(report.ok)

    def test_authority_three_without_approval_is_rejected_at_ir(self) -> None:
        doc = _doc("ir_valid_minimal.json")
        doc["authority"] = 3
        report = self._runner().run(doc)
        self.assertFalse(report.ok)
        self.assertEqual(report.stage, "ir")
        self.assertEqual(report.findings[0].rule_id, "IR-04")

    def test_critical_capability_without_ensemble_is_rejected(self) -> None:
        doc = _doc("ir_valid_critical.json")
        doc["redundancy"]["min_agreement"] = 1
        report = self._runner().run(doc)
        self.assertFalse(report.ok)
        self.assertEqual(report.stage, "ir")
        self.assertEqual(report.findings[0].rule_id, "IR-12")


if __name__ == "__main__":
    unittest.main()
