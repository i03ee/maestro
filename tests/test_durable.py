"""اختبارات التنفيذ المتين: لا تنفيذ مرّتين، واستئناف بعد الموت."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from maestro.durable.journal import DurableJournal
from maestro.durable.runner import DurableRunner
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


class DurableCase(unittest.TestCase):
    """أدوات بناء."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.journal = DurableJournal(Path(self._tmp.name) / "journal.jsonl")
        self.registry = CapabilityRegistry()
        self.registry.register(
            CapabilitySpec(
                name="media.render",
                description_ar="توليد صورة",
                required_tools=("render.image",),
                default_authority=1,
            )
        )
        self.permissions = PermissionGuard(
            allowed_capabilities=frozenset({"media.render"}), max_authority=2
        )
        self.provider = ScriptedProvider("local", [_response()])
        self.router = ModelRouter(
            providers={"local": self.provider},
            profiles={"local": PROFILE},
            policy=RoutingPolicy(),
            budget=BudgetGuard(max_cost_usd=1.0, max_tokens=100_000),
        )
        self.capability_runner = CapabilityRunner(self.registry, self.router, self.permissions)
        self.runner = DurableRunner(self.capability_runner, self.journal)

    def tearDown(self) -> None:
        self._tmp.cleanup()


class TestJournal(DurableCase):
    """السجل إلحاقي."""

    def test_append_and_read_back(self) -> None:
        self.journal.append(
            task_id="t1",
            event="started",
            idempotency_key="t1:media.render",
            capability="media.render",
        )
        records = self.journal.records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].seq, 1)
        self.assertEqual(records[0].event, "started")

    def test_sequence_numbers_are_continuous(self) -> None:
        for index in range(3):
            self.journal.append(
                task_id=f"t{index}",
                event="started",
                idempotency_key=f"k{index}",
                capability="media.render",
            )
        self.assertEqual([r.seq for r in self.journal.records()], [1, 2, 3])

    def test_pending_excludes_finished_tasks(self) -> None:
        self.journal.append(
            task_id="t1", event="started", idempotency_key="k1", capability="media.render"
        )
        self.journal.append(
            task_id="t1", event="finished", idempotency_key="k1", capability="media.render"
        )
        self.assertEqual(self.journal.pending(), [])


class TestIdempotency(DurableCase):
    """المهمة لا تُنفَّذ مرّتين."""

    def test_first_execution_runs(self) -> None:
        outcome = self.runner.execute("t1", _doc("ir_valid_minimal.json"))
        self.assertEqual(outcome.status, "done")
        self.assertTrue(outcome.report.ok)
        self.assertEqual(len(self.provider.calls), 1)

    def test_second_execution_is_cached_without_calling_model(self) -> None:
        self.runner.execute("t1", _doc("ir_valid_minimal.json"))
        outcome = self.runner.execute("t1", _doc("ir_valid_minimal.json"))
        self.assertEqual(outcome.status, "cached")
        self.assertTrue(outcome.report.ok)
        self.assertEqual(outcome.report.output, "نتيجة")
        self.assertEqual(len(self.provider.calls), 1)

    def test_different_key_executes_again(self) -> None:
        self.provider.script.append(_response("نتيجة ثانية"))
        self.runner.execute("t1", _doc("ir_valid_minimal.json"), idempotency_key="k1")
        outcome = self.runner.execute("t2", _doc("ir_valid_minimal.json"), idempotency_key="k2")
        self.assertEqual(outcome.status, "done")
        self.assertEqual(len(self.provider.calls), 2)


class TestCrashAndResume(DurableCase):
    """موت العملية بين «بدأت» و«انتهت» لا يُفقد المهمة."""

    def test_crash_leaves_task_pending(self) -> None:
        doc = _doc("ir_valid_minimal.json")
        self.journal.append(
            task_id="t1",
            event="started",
            idempotency_key="t1:media.render",
            capability="media.render",
            payload={"doc": doc},
        )
        pending = self.journal.pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].task_id, "t1")

    def test_resume_completes_the_task(self) -> None:
        doc = _doc("ir_valid_minimal.json")
        self.journal.append(
            task_id="t1",
            event="started",
            idempotency_key="t1:media.render",
            capability="media.render",
            payload={"doc": doc},
        )
        outcomes = self.runner.resume_pending()
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0].status, "done")
        self.assertTrue(outcomes[0].report.ok)
        self.assertEqual(len(self.provider.calls), 1)
        self.assertEqual(self.journal.pending(), [])

    def test_resume_after_completion_does_nothing(self) -> None:
        self.runner.execute("t1", _doc("ir_valid_minimal.json"))
        outcomes = self.runner.resume_pending()
        self.assertEqual(outcomes, [])
        self.assertEqual(len(self.provider.calls), 1)


class TestFailure(DurableCase):
    """الفشل يُسجَّل ولا يُعَدّ إنجازاً."""

    def test_failed_task_is_journaled_and_not_cached(self) -> None:
        doc = _doc("ir_valid_minimal.json")
        doc["ir_version"] = "0.9"
        outcome = self.runner.execute("t1", doc)
        self.assertEqual(outcome.status, "failed")
        self.assertFalse(outcome.report.ok)
        events = [record.event for record in self.journal.records()]
        self.assertEqual(events, ["started", "failed"])
        self.assertIsNone(self.journal.completed("t1:media.render"))

    def test_rejected_task_can_be_retried_after_fix(self) -> None:
        broken = _doc("ir_valid_minimal.json")
        broken["ir_version"] = "0.9"
        self.assertEqual(self.runner.execute("t1", broken).status, "failed")
        fixed = _doc("ir_valid_minimal.json")
        outcome = self.runner.execute("t1", fixed)
        self.assertEqual(outcome.status, "done")


if __name__ == "__main__":
    unittest.main()
