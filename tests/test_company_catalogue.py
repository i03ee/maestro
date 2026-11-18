"""اختبارات كتالوج الشركة: 8 نطاقات · 24 قدرة · 4 استدعاءات لبوابة واحدة."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from maestro.company import (
    CAPABILITIES,
    COMMUNITY_GATE,
    DOMAINS,
    GATE_INVOCATIONS,
    build_registry,
    by_domain,
    capability_by_name,
    capability_to_ir,
    check_catalogue,
    critical_capabilities,
    edges,
    specialization_targets,
    topology_report,
)
from maestro.ir.validate import ALLOWED_TOOLS, validate_ir

ROOT = Path(__file__).resolve().parent.parent


class TestShape(unittest.TestCase):
    """الأرقام المعلنة في وثيقة الشركة."""

    def test_eight_domains(self) -> None:
        self.assertEqual(len(DOMAINS), 8)

    def test_twenty_four_capabilities(self) -> None:
        self.assertEqual(len(CAPABILITIES), 24)

    def test_capability_names_are_unique(self) -> None:
        names = [capability.name for capability in CAPABILITIES]
        self.assertEqual(len(set(names)), len(names))

    def test_agent_per_capability_is_one_to_one(self) -> None:
        agents = [capability.agent for capability in CAPABILITIES]
        self.assertEqual(len(set(agents)), len(agents))

    def test_every_capability_belongs_to_a_known_domain(self) -> None:
        domain_keys = {domain.key for domain in DOMAINS}
        for capability in CAPABILITIES:
            with self.subTest(capability=capability.name):
                self.assertIn(capability.domain, domain_keys)

    def test_every_domain_has_at_least_one_capability(self) -> None:
        grouped = by_domain()
        for domain in DOMAINS:
            with self.subTest(domain=domain.key):
                self.assertTrue(grouped[domain.key])


class TestCatalogueIsConsistent(unittest.TestCase):
    """فحص الكتالوج نفسه لا يجد مشاكل."""

    def test_no_problems(self) -> None:
        self.assertEqual(check_catalogue(), [])

    def test_tools_are_within_the_allow_list(self) -> None:
        for capability in CAPABILITIES:
            for tool in capability.tools:
                with self.subTest(capability=capability.name, tool=tool):
                    self.assertIn(tool, ALLOWED_TOOLS)


class TestCriticalCapabilities(unittest.TestCase):
    """القدرات الحرجة: نموذجان واتفاق نموذجين وبوابة."""

    def test_critical_needs_two_models(self) -> None:
        for capability in critical_capabilities():
            with self.subTest(capability=capability.name):
                self.assertGreaterEqual(len(capability.ensemble), 2)

    def test_critical_needs_agreement_of_two(self) -> None:
        for capability in critical_capabilities():
            with self.subTest(capability=capability.name):
                self.assertGreaterEqual(capability.min_agreement, 2)

    def test_agreement_is_a_count_not_a_ratio(self) -> None:
        for capability in CAPABILITIES:
            with self.subTest(capability=capability.name):
                self.assertIsInstance(capability.min_agreement, int)
                self.assertLessEqual(capability.min_agreement, len(capability.ensemble))

    def test_critical_is_a_gate_or_has_one(self) -> None:
        gate_names = {edge.target for edge in edges()}
        for capability in critical_capabilities():
            with self.subTest(capability=capability.name):
                self.assertTrue(capability.gates or capability.name in gate_names)


class TestCommunityGate(unittest.TestCase):
    """بوابة واحدة، أربعة استدعاءات."""

    def test_gate_is_defined_once(self) -> None:
        self.assertIsNotNone(capability_by_name(COMMUNITY_GATE))

    def test_four_invocations(self) -> None:
        self.assertEqual(len(GATE_INVOCATIONS), 4)
        self.assertEqual(len(set(GATE_INVOCATIONS)), 4)

    def test_every_invocation_calls_the_gate(self) -> None:
        for invocation in GATE_INVOCATIONS:
            with self.subTest(invocation=invocation):
                capability = capability_by_name(invocation)
                self.assertIsNotNone(capability)
                self.assertIn(COMMUNITY_GATE, capability.gates)

    def test_one_gate_many_edges(self) -> None:
        """أربع وصلات تدخل البوابة نفسها — لا أربع بوابات."""
        incoming = [edge for edge in edges() if edge.target == COMMUNITY_GATE]
        self.assertEqual(len(incoming), 4)


class TestTopology(unittest.TestCase):
    """شبكة الاعتماد."""

    def test_no_dangling_edges(self) -> None:
        for edge in edges():
            with self.subTest(edge=f"{edge.source}->{edge.target}"):
                self.assertIsNotNone(capability_by_name(edge.source))
                self.assertIsNotNone(capability_by_name(edge.target))

    def test_every_domain_is_connected(self) -> None:
        """لا نطاق معزول: كل نطاق له قدرة تتصل بغيرها أو تُستدعى."""
        connected = {edge.source for edge in edges()} | {edge.target for edge in edges()}
        for domain in DOMAINS:
            names = {capability.name for capability in by_domain()[domain.key]}
            with self.subTest(domain=domain.key):
                self.assertTrue(names & connected)

    def test_release_is_gated_by_qa_and_security(self) -> None:
        publish = capability_by_name("release.release_publish")
        self.assertIn("release.release_signing", publish.gates)
        self.assertIn("quality.data_security", publish.gates)

    def test_payment_is_gated_by_security(self) -> None:
        payment = capability_by_name("engineering.payment_interface")
        self.assertIn("quality.data_security", payment.gates)


class TestRegistryBridge(unittest.TestCase):
    """الجسر من الكتالوج إلى سجل التشغيل."""

    def test_registry_contains_every_capability(self) -> None:
        registry = build_registry()
        for capability in CAPABILITIES:
            with self.subTest(capability=capability.name):
                self.assertIsNotNone(registry.get(capability.name))

    def test_registry_contains_specializations(self) -> None:
        registry = build_registry()
        targets = specialization_targets()
        self.assertIn("catalog.ingest", targets)
        self.assertIsNotNone(registry.get("catalog.ingest"))

    def test_ir_document_generated_from_catalogue_passes_rules(self) -> None:
        for capability in CAPABILITIES:
            with self.subTest(capability=capability.name):
                doc = capability_to_ir(capability, "نيّة الاختبار", human_approved=True)
                errors = [f for f in validate_ir(doc) if f.severity == "error"]
                self.assertEqual(errors, [], msg=str(errors))

    def test_authority_three_is_refused_without_approval(self) -> None:
        """الصلاحية 3 لا تُفترض — تُرفض حتى بموافقة مسجّلة."""
        for capability in CAPABILITIES:
            if capability.authority < 3:
                continue
            with self.subTest(capability=capability.name):
                doc = capability_to_ir(capability, "نيّة الاختبار")
                errors = [f for f in validate_ir(doc) if f.severity == "error"]
                self.assertEqual([f.rule_id for f in errors], ["IR-04"])


class TestGeneratedDocument(unittest.TestCase):
    """الوثيقة المولَّدة لا تنحرف عن الشيفرة."""

    def test_document_matches_code(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/catalogue_report.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)


class TestReport(unittest.TestCase):
    """ملخّص الطوبولوجيا."""

    def test_report_numbers(self) -> None:
        report = topology_report()
        self.assertEqual(report["domains"], 8)
        self.assertEqual(report["capabilities"], 24)
        self.assertEqual(report["community_gate_invocations"], 4)


if __name__ == "__main__":
    unittest.main()
