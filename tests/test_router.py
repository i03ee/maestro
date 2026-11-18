"""اختبارات الموجّه: الإسقاط، الميزانية، وسجل الأدلة."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from maestro.evidence.log import EvidenceLog
from maestro.guards.budget import BudgetExceeded, BudgetGuard
from maestro.routing.base import (
    CompletionRequest,
    CompletionResponse,
    ModelProfile,
    RoutingPolicy,
)
from maestro.routing.offline import ScriptedProvider
from maestro.routing.router import ModelRouter, RoutingFailure

LOCAL = ModelProfile(
    name="local",
    tier="local",
    model="qwen-local",
    cost_in_per_mtok=0.0,
    cost_out_per_mtok=0.0,
    max_context=32768,
)
API = ModelProfile(
    name="api",
    tier="api",
    model="deepseek-flash",
    cost_in_per_mtok=0.15,
    cost_out_per_mtok=0.60,
    max_context=1_000_000,
    api_key_env="MAESTRO_TEST_KEY",
)
FALLBACK = ModelProfile(
    name="fallback",
    tier="fallback",
    model="backup-model",
    cost_in_per_mtok=0.10,
    cost_out_per_mtok=0.40,
    max_context=200_000,
)
PROFILES = {"local": LOCAL, "api": API, "fallback": FALLBACK}


def _response(text: str, tokens_in: int = 100, tokens_out: int = 50) -> CompletionResponse:
    return CompletionResponse(text=text, tokens_in=tokens_in, tokens_out=tokens_out, model="m")


def _router(
    providers: dict,
    budget: BudgetGuard | None = None,
    policy: RoutingPolicy | None = None,
    profiles: dict | None = None,
):
    return ModelRouter(
        providers=providers,
        profiles=profiles if profiles is not None else PROFILES,
        policy=policy or RoutingPolicy(),
        budget=budget or BudgetGuard(max_cost_usd=1.0, max_tokens=100_000),
    )


class TestHappyPath(unittest.TestCase):
    """النجاح المباشر."""

    def test_first_provider_wins(self) -> None:
        provider = ScriptedProvider("local", [_response("نتيجة")])
        router = _router({"local": provider, "api": ScriptedProvider("api", [])})
        result = router.run(CompletionRequest(capability="media.render", prompt="س"))
        self.assertEqual(result.provider, "local")
        self.assertFalse(result.fallback_used)
        self.assertEqual(len(result.attempts), 1)
        self.assertEqual(result.attempts[0].status, "ok")

    def test_cost_is_computed_from_profile(self) -> None:
        router = _router({"local": ScriptedProvider("local", [_response("نتيجة")])})
        result = router.run(CompletionRequest(capability="media.render", prompt="س"))
        self.assertEqual(result.cost_usd, 0.0)
        self.assertEqual(result.tokens_in, 100)
        self.assertEqual(result.tokens_out, 50)


class TestFallback(unittest.TestCase):
    """الإسقاط منظّم."""

    def test_failure_falls_to_next_provider(self) -> None:
        providers = {
            "local": ScriptedProvider("local", [RuntimeError("تعطّل")]),
            "api": ScriptedProvider("api", [_response("نتيجة")]),
            "fallback": ScriptedProvider("fallback", []),
        }
        router = _router(providers)
        os.environ["MAESTRO_TEST_KEY"] = "test-key"
        try:
            result = router.run(CompletionRequest(capability="media.render", prompt="س"))
        finally:
            del os.environ["MAESTRO_TEST_KEY"]
        self.assertEqual(result.provider, "api")
        self.assertTrue(result.fallback_used)
        self.assertEqual([a.status for a in result.attempts], ["failed", "ok"])

    def test_empty_output_falls_through(self) -> None:
        providers = {
            "local": ScriptedProvider("local", [_response("   ")]),
            "fallback": ScriptedProvider("fallback", [_response("نتيجة")]),
        }
        router = _router(providers, profiles={"local": LOCAL, "fallback": FALLBACK})
        result = router.run(CompletionRequest(capability="media.render", prompt="س"))
        self.assertEqual(result.provider, "fallback")
        self.assertEqual([a.status for a in result.attempts], ["empty_output", "ok"])

    def test_all_failures_raise_with_attempts(self) -> None:
        providers = {
            "local": ScriptedProvider("local", [RuntimeError("أ")]),
            "fallback": ScriptedProvider("fallback", [RuntimeError("ب")]),
        }
        router = _router(providers, profiles={"local": LOCAL, "fallback": FALLBACK})
        with self.assertRaises(RoutingFailure) as caught:
            router.run(CompletionRequest(capability="media.render", prompt="س"))
        self.assertEqual(len(caught.exception.attempts), 2)
        self.assertEqual(
            [a.status for a in caught.exception.attempts], ["failed", "failed"]
        )

    def test_missing_credentials_are_skipped_not_called(self) -> None:
        providers = {
            "local": ScriptedProvider("local", [RuntimeError("تعطّل")]),
            "api": ScriptedProvider("api", [_response("لن تُستدعى")]),
            "fallback": ScriptedProvider("fallback", [_response("نتيجة")]),
        }
        router = _router(providers)
        os.environ.pop("MAESTRO_TEST_KEY", None)
        result = router.run(CompletionRequest(capability="media.render", prompt="س"))
        self.assertEqual(result.provider, "fallback")
        statuses = [a.status for a in result.attempts]
        self.assertEqual(statuses, ["failed", "skipped_missing_credentials", "ok"])
        self.assertEqual(providers["api"].calls, [])

    def test_provider_without_tools_support_is_skipped(self) -> None:
        no_tools = ModelProfile(
            name="local",
            tier="local",
            model="m",
            cost_in_per_mtok=0.0,
            cost_out_per_mtok=0.0,
            max_context=4096,
            supports_tools=False,
        )
        router = ModelRouter(
            providers={"local": ScriptedProvider("local", [_response("نتيجة")])},
            profiles={"local": no_tools},
            policy=RoutingPolicy(),
            budget=BudgetGuard(),
        )
        with self.assertRaises(RoutingFailure) as caught:
            router.run(
                CompletionRequest(capability="media.render", prompt="س", tools=("render.image",))
            )
        self.assertEqual(
            [a.status for a in caught.exception.attempts], ["skipped_tool_unsupported"]
        )


class TestBudgetGate(unittest.TestCase):
    """الميزانية سقف صلب: يوقف ولا يُسقَط."""

    def test_over_budget_stops_before_any_call(self) -> None:
        provider = ScriptedProvider("local", [_response("نتيجة")])
        router = _router(
            {"local": provider},
            budget=BudgetGuard(max_cost_usd=1.0, max_tokens=10),
        )
        with self.assertRaises(BudgetExceeded):
            router.run(CompletionRequest(capability="media.render", prompt="س"))
        self.assertEqual(provider.calls, [])

    def test_consumption_is_recorded(self) -> None:
        budget = BudgetGuard(max_cost_usd=1.0, max_tokens=100_000)
        router = _router({"local": ScriptedProvider("local", [_response("نتيجة")])}, budget=budget)
        router.run(CompletionRequest(capability="media.render", prompt="س"))
        self.assertEqual(budget.spent_tokens, 150)


class TestEvidence(unittest.TestCase):
    """كل تنفيذ ناجح يُترك أثراً في سجل الأدلة."""

    def test_successful_run_appends_verifiable_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = EvidenceLog(Path(tmp) / "evidence.jsonl")
            router = _router(
                {"local": ScriptedProvider("local", [_response("نتيجة")])}, policy=RoutingPolicy()
            )
            router.evidence = log
            router.run(CompletionRequest(capability="media.render", prompt="س"))
            entries = log.entries()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].kind, "routing")
            self.assertTrue(log.verify())


if __name__ == "__main__":
    unittest.main()
