"""اختبارات عقود القدرات: ٢٤ عقداً، وكلٌّ اجتاز القواعد أو مرفوض بقاعدة واحدة."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from maestro.company.catalogue import CAPABILITIES, capability_by_name
from maestro.company.contracts import all_contracts, check_contracts, contract_for
from maestro.ir.validate import validate_ir

ROOT = Path(__file__).resolve().parent.parent


class TestContracts(unittest.TestCase):
    """العقود المولَّدة."""

    def test_every_capability_has_a_contract(self) -> None:
        contracts = all_contracts()
        self.assertEqual(len(contracts), len(CAPABILITIES))
        for capability in CAPABILITIES:
            with self.subTest(capability=capability.name):
                self.assertIn(capability.name, contracts)

    def test_contracts_have_no_problems(self) -> None:
        self.assertEqual(check_contracts(), [])

    def test_contract_carries_the_catalogue_agent(self) -> None:
        capability = capability_by_name("engineering.code_review")
        document = contract_for(capability)
        self.assertEqual(document["steps"][0]["agent"], capability.agent)
        self.assertEqual(document["steps"][0]["tools"], list(capability.tools))

    def test_authority_three_is_never_assumed(self) -> None:
        """الصلاحية 3: العقد مرفوض بلا موافقة، ويمرّ بموافقة مسجّلة."""
        capability = capability_by_name("release.release_publish")
        document = contract_for(capability)
        errors = [f.rule_id for f in validate_ir(document) if f.severity == "error"]
        self.assertEqual(errors, ["IR-04"])
        document["human_approval"] = True
        errors = [f.rule_id for f in validate_ir(document) if f.severity == "error"]
        self.assertEqual(errors, [])

    def test_critical_capabilities_carry_agreement(self) -> None:
        for capability in CAPABILITIES:
            if not capability.critical:
                continue
            with self.subTest(capability=capability.name):
                document = contract_for(capability)
                self.assertGreaterEqual(document["redundancy"]["min_agreement"], 2)


class TestGeneratedDocument(unittest.TestCase):
    """وثيقة العقود لا تنحرف عن الشيفرة."""

    def test_document_matches_code(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/contracts_report.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_document_lists_every_capability(self) -> None:
        payload = json.loads(
            (ROOT / "docs" / "CAPABILITY_CONTRACTS.json").read_text(encoding="utf-8")
        )
        self.assertEqual(payload["count"], len(CAPABILITIES))
        self.assertEqual(len(payload["contracts"]), len(CAPABILITIES))


if __name__ == "__main__":
    unittest.main()
