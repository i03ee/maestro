"""اختبارات سجل الأدلة: إلحاقي بسلسلة بصمات."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from maestro.evidence.log import GENESIS, EvidenceLog


class TestEvidenceLog(unittest.TestCase):
    """أي تعديل على سجل سابق يكسر السلسلة ويُكشف."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "evidence.jsonl"
        self.log = EvidenceLog(self.path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_empty_log_verifies(self) -> None:
        self.assertEqual(self.log.entries(), [])
        self.assertTrue(self.log.verify())
        self.assertEqual(self.log.head_hash, GENESIS)

    def test_append_builds_chain(self) -> None:
        self.log.append("routing", {"capability": "media.render"})
        self.log.append("routing", {"capability": "catalog.ingest"})
        entries = self.log.entries()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].prev_hash, GENESIS)
        self.assertEqual(entries[1].prev_hash, entries[0].entry_hash)
        self.assertTrue(self.log.verify())

    def test_tampering_breaks_verification(self) -> None:
        self.log.append("routing", {"capability": "media.render"})
        self.log.append("routing", {"capability": "catalog.ingest"})
        lines = self.path.read_text(encoding="utf-8").splitlines()
        payload = json.loads(lines[0])
        payload["payload"]["capability"] = "payment.capture"
        lines[0] = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.assertFalse(EvidenceLog(self.path).verify())

    def test_deleting_a_line_breaks_verification(self) -> None:
        self.log.append("routing", {"a": 1})
        self.log.append("routing", {"b": 2})
        lines = self.path.read_text(encoding="utf-8").splitlines()
        self.path.write_text(lines[1] + "\n", encoding="utf-8")
        self.assertFalse(EvidenceLog(self.path).verify())

    def test_entry_hash_is_deterministic(self) -> None:
        first = EvidenceLog(Path(self._tmp.name) / "a.jsonl")
        second = EvidenceLog(Path(self._tmp.name) / "b.jsonl")
        self.assertEqual(
            first.append("routing", {"x": 1, "y": "ع"}),
            second.append("routing", {"x": 1, "y": "ع"}),
        )


if __name__ == "__main__":
    unittest.main()
