"""اختبارات المنتجات: من ردّ منظَّم إلى artefact مسمّى، والعكس يُرفض."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from maestro.producers.idea import (
    produce_prd,
    validate_prd_payload,
    write_prd,
)
from maestro.producers.research import (
    produce_candidates,
    produce_competitors,
    validate_candidates,
    validate_competitors,
    write_candidates,
    write_competitors,
)
from maestro.producers.structured import StructuredResponseError

VALID_IDEA = {
    "product_name": "منصة نَسمة",
    "problem": "غياب منصة تجارة جمال بالكردية.",
    "features": [
        {
            "id": "F-1",
            "title": "كتالوج",
            "priority": "must",
            "story": "كزبون.",
            "criteria": ["ثلاث لغات"],
        },
        {
            "id": "F-2",
            "title": "لوحة",
            "priority": "should",
            "story": "كمورد.",
            "criteria": ["عرض المخزون"],
        },
    ],
}

VALID_COMPETITORS = {
    "competitors": [
        {"name": "أ", "url": "https://a", "strengths": "x", "weaknesses": "y", "price_point": "z", "source": "https://a/s"},
        {"name": "ب", "url": "https://b", "strengths": "x", "weaknesses": "y", "price_point": "z", "source": "https://b/s"},
        {"name": "ج", "url": "https://c", "strengths": "x", "weaknesses": "y", "price_point": "z", "source": "https://c/s"},
    ]
}

VALID_CANDIDATES = {
    "candidates": [
        {
            "name": "saleor",
            "source": "https://github.com/saleor/saleor",
            "spdx": "BSD-3-Clause",
            "scan_result": "clean",
            "decision": "allow",
            "reason": "رخصة تسمح بالاستعمال.",
        }
    ]
}


def _dump(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)


class TestPrdProducer(unittest.TestCase):
    """منتج المتطلبات."""

    def test_valid_payload_produces_prd_and_stories(self) -> None:
        result = produce_prd(_dump(VALID_IDEA))
        self.assertEqual(result.product_name, "منصة نَسمة")
        self.assertEqual(len(result.features), 2)
        self.assertIn("F-1", result.prd_markdown)
        self.assertEqual(len(result.as_user_stories()), 2)

    def test_every_must_feature_has_story_and_criteria(self) -> None:
        result = produce_prd(_dump(VALID_IDEA))
        must = [f for f in result.features if f.priority == "must"]
        self.assertTrue(must)
        for feature in must:
            self.assertTrue(feature.story.strip())
            self.assertTrue(feature.criteria)

    def test_missing_criteria_is_rejected(self) -> None:
        payload = json.loads(_dump(VALID_IDEA))
        payload["features"][0]["criteria"] = []
        with self.assertRaises(StructuredResponseError):
            produce_prd(_dump(payload))

    def test_missing_source_of_truth_is_rejected(self) -> None:
        payload = json.loads(_dump(VALID_IDEA))
        del payload["problem"]
        self.assertTrue(validate_prd_payload(payload))

    def test_non_json_is_rejected(self) -> None:
        with self.assertRaises(StructuredResponseError):
            produce_prd("نص حرّ")

    def test_artefacts_are_written(self) -> None:
        result = produce_prd(_dump(VALID_IDEA))
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_prd(result, tmp)
            self.assertTrue(paths["prd"].is_file())
            self.assertTrue(paths["user_stories"].is_file())
            stories = json.loads(paths["user_stories"].read_text(encoding="utf-8"))
            self.assertEqual(len(stories), 2)


class TestCompetitorProducer(unittest.TestCase):
    """منتج المنافسين."""

    def test_three_competitors_with_sources(self) -> None:
        result = produce_competitors(_dump(VALID_COMPETITORS))
        self.assertEqual(len(result.competitors), 3)

    def test_fewer_than_three_is_rejected(self) -> None:
        payload = {"competitors": VALID_COMPETITORS["competitors"][:2]}
        self.assertTrue(validate_competitors(payload))
        with self.assertRaises(StructuredResponseError):
            produce_competitors(_dump(payload))

    def test_row_without_source_is_rejected(self) -> None:
        payload = json.loads(_dump(VALID_COMPETITORS))
        payload["competitors"][0]["source"] = ""
        self.assertTrue(validate_competitors(payload))

    def test_csv_has_a_source_per_row(self) -> None:
        result = produce_competitors(_dump(VALID_COMPETITORS))
        with tempfile.TemporaryDirectory() as tmp:
            path = write_competitors(result, tmp)
            rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
            self.assertEqual(len(rows), 3)
            for row in rows:
                self.assertTrue(row["source"].strip())


class TestCandidateProducer(unittest.TestCase):
    """منتج المرشّحين."""

    def test_candidates_carry_license_scan_and_reason(self) -> None:
        result = produce_candidates(_dump(VALID_CANDIDATES))
        candidate = result.candidates[0]
        self.assertEqual(candidate.spdx, "BSD-3-Clause")
        self.assertEqual(candidate.decision, "allow")
        self.assertTrue(candidate.reason.strip())

    def test_empty_candidate_list_is_rejected(self) -> None:
        self.assertTrue(validate_candidates({"candidates": []}))

    def test_unknown_decision_is_rejected(self) -> None:
        payload = json.loads(_dump(VALID_CANDIDATES))
        payload["candidates"][0]["decision"] = "maybe"
        self.assertTrue(validate_candidates(payload))

    def test_missing_reason_is_rejected(self) -> None:
        payload = json.loads(_dump(VALID_CANDIDATES))
        payload["candidates"][0]["reason"] = ""
        self.assertTrue(validate_candidates(payload))

    def test_all_three_artefacts_are_written(self) -> None:
        result = produce_candidates(_dump(VALID_CANDIDATES))
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_candidates(result, tmp)
            self.assertTrue(paths["candidates"].is_file())
            self.assertTrue(paths["scans"].is_file())
            self.assertTrue(paths["decisions"].is_file())


if __name__ == "__main__":
    unittest.main()
