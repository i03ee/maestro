"""اختبارات عقد IR: القواعد الأربع عشرة، والحالات الذهبية."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from maestro.ir import RULES_BY_ID, is_valid_ir, rule_ids, validate_ir
from maestro.ir.validate import errors_only

GOLDEN = Path(__file__).parent / "golden"


def _load(name: str) -> dict:
    return json.loads((GOLDEN / name).read_text(encoding="utf-8"))


def _apply(doc: dict, mutations: dict) -> dict:
    """يطبّق تعديلات على مسارات منقوطة: steps.0.tools."""
    result = copy.deepcopy(doc)
    for path, value in mutations.items():
        parts = path.split(".")
        target = result
        for part in parts[:-1]:
            target = target[int(part)] if part.isdigit() else target[part]
        last = parts[-1]
        if last.isdigit():
            target[int(last)] = value
        else:
            target[last] = value
    return result


class TestRuleTable(unittest.TestCase):
    """جدول القواعد نفسه."""

    def test_fourteen_rules_present_and_unique(self) -> None:
        self.assertEqual(len(rule_ids()), 14)
        self.assertEqual(len(set(rule_ids())), 14)

    def test_rule_ids_are_sequential(self) -> None:
        self.assertEqual(
            list(rule_ids()), [f"IR-{index:02d}" for index in range(1, 15)]
        )

    def test_every_rule_has_arabic_title_and_rationale(self) -> None:
        for rule_id, rule in RULES_BY_ID.items():
            with self.subTest(rule=rule_id):
                self.assertTrue(rule.title_ar.strip())
                self.assertTrue(rule.rationale_ar.strip())
                self.assertIn(rule.severity, {"error", "warning", "info"})


class TestGoldenDocuments(unittest.TestCase):
    """المستندات الذهبية."""

    def test_minimal_document_passes(self) -> None:
        doc = _load("ir_valid_minimal.json")
        self.assertTrue(is_valid_ir(doc), msg=str(errors_only(validate_ir(doc))))

    def test_critical_document_passes(self) -> None:
        doc = _load("ir_valid_critical.json")
        self.assertTrue(is_valid_ir(doc), msg=str(errors_only(validate_ir(doc))))

    def test_critical_document_requires_agreement_count(self) -> None:
        """الاتفاق عدد صحيح لا نسبة: 2 من 3 تُقبل، ونسبة مئوية تُرفض."""
        doc = _load("ir_valid_critical.json")
        self.assertEqual(doc["redundancy"]["min_agreement"], 2)
        self.assertIsInstance(doc["redundancy"]["min_agreement"], int)


class TestInvalidExamples(unittest.TestCase):
    """كل حالة خاطئة تُنتج قاعدتها بالضبط — لا أكثر ولا أقل."""

    def test_each_case_fails_exactly_its_rule(self) -> None:
        base = _load("ir_valid_minimal.json")
        cases = _load("ir_invalid_examples.json")["cases"]
        self.assertGreaterEqual(len(cases), 14)
        for case in cases:
            with self.subTest(case=case["id"]):
                doc = _apply(base, case["mutations"])
                error_rules = {finding.rule_id for finding in errors_only(validate_ir(doc))}
                self.assertEqual(error_rules, {case["expect_rule"]})

    def test_valid_base_is_not_rejected(self) -> None:
        base = _load("ir_valid_minimal.json")
        self.assertEqual(errors_only(validate_ir(base)), [])


class TestDeterminism(unittest.TestCase):
    """الفحص حتمي: نفس المستند ⇒ نفس الملاحظات بالترتيب نفسه."""

    def test_findings_are_stable_across_runs(self) -> None:
        doc = _load("ir_invalid_examples.json")["cases"][0]
        base = _load("ir_valid_minimal.json")
        first = [f.as_dict() for f in validate_ir(_apply(base, doc["mutations"]))]
        second = [f.as_dict() for f in validate_ir(_apply(base, doc["mutations"]))]
        self.assertEqual(first, second)
        self.assertGreaterEqual(len(first), 1)

    def test_rule_order_is_fixed(self) -> None:
        base = _load("ir_valid_minimal.json")
        findings = validate_ir(_apply(base, {"ir_version": "0.9", "capability": "X"}))
        self.assertEqual([f.rule_id for f in findings], ["IR-01", "IR-02"])


if __name__ == "__main__":
    unittest.main()
