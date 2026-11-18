"""اختبارات الخط الأساسي: قياس قبل التحسين."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from maestro.baseline.recorder import BaselineRecorder


class TestBaselineRecorder(unittest.TestCase):
    """الأرقام تُقارن بخط الأساس، ولا تتحوّل إلى بوابة قبول."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.recorder = BaselineRecorder(Path(self._tmp.name) / "baseline.jsonl")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_three(self) -> None:
        self.recorder.record(
            capability="catalog.ingest",
            output_id="p1",
            human_minutes=10,
            cost_usd=0.10,
            accepted_unedited=True,
            repeat_within_2_weeks=False,
            timestamp="2026-11-18T10:00:00Z",
        )
        self.recorder.record(
            capability="catalog.ingest",
            output_id="p2",
            human_minutes=20,
            cost_usd=0.20,
            accepted_unedited=False,
            repeat_within_2_weeks=True,
            timestamp="2026-11-18T11:00:00Z",
        )
        self.recorder.record(
            capability="media.render",
            output_id="i1",
            human_minutes=5,
            cost_usd=0.50,
            accepted_unedited=True,
            timestamp="2026-11-18T12:00:00Z",
        )

    def test_empty_summary(self) -> None:
        summary = self.recorder.summary("catalog.ingest")
        self.assertEqual(summary["outputs"], 0)
        self.assertIsNone(summary["mean_human_minutes"])

    def test_summary_aggregates_per_capability(self) -> None:
        self._write_three()
        summary = self.recorder.summary("catalog.ingest")
        self.assertEqual(summary["outputs"], 2)
        self.assertEqual(summary["mean_human_minutes"], 15.0)
        self.assertAlmostEqual(summary["mean_cost_usd"], 0.15)
        self.assertEqual(summary["accepted_unedited"], 0.5)

    def test_summary_across_capabilities(self) -> None:
        self._write_three()
        summary = self.recorder.summary()
        self.assertEqual(summary["outputs"], 3)
        self.assertAlmostEqual(summary["mean_human_minutes"], 35 / 3)

    def test_repeat_rate_ignores_unknown_rows(self) -> None:
        self._write_three()
        summary = self.recorder.summary()
        self.assertAlmostEqual(summary["repeat_within_2_weeks"], 0.5)

    def test_records_are_persisted_as_jsonl(self) -> None:
        self._write_three()
        lines = self.recorder.path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 3)
        self.assertIn('"capability"', lines[0])


if __name__ == "__main__":
    unittest.main()
