"""اختبارات طبقة الوكلاء الحيّة.

اختبارات الجسر المتزامن تعمل في كل مكان. اختبارات PydanticAI نفسه تحتاج
الحزمة الاختيارية، فتُتخطّى محلياً وتعمل في CI حيث تُثبَّت المجموعة.
"""

from __future__ import annotations

import asyncio
import unittest

from maestro.agents._sync import AgentLayerError, run_sync
from maestro.routing.base import CompletionRequest, ModelProfile

PROFILE = ModelProfile(
    name="api",
    tier="api",
    model="deepseek-flash",
    cost_in_per_mtok=0.15,
    cost_out_per_mtok=0.60,
    max_context=1_000_000,
)

try:  # pragma: no cover
    from maestro.agents.pydanticai_layer import (
        PYDANTIC_AI_AVAILABLE,
        PydanticAIProvider,
        build_deepseek_agent,
    )
except Exception:  # pragma: no cover
    PYDANTIC_AI_AVAILABLE = False


class TestSyncBridge(unittest.TestCase):
    """الجسر بين الواجهة المتزامنة والنواة غير المتزامنة."""

    def test_coroutine_runs_to_completion(self) -> None:
        async def work() -> int:
            await asyncio.sleep(0)
            return 7

        self.assertEqual(run_sync(work), 7)

    def test_called_inside_running_loop_is_refused(self) -> None:
        async def outer() -> None:
            async def inner() -> int:
                return 1

            with self.assertRaises(AgentLayerError):
                run_sync(inner)

        asyncio.run(outer())


@unittest.skipUnless(PYDANTIC_AI_AVAILABLE, "pydantic-ai غير مثبّت")
class TestPydanticAIProvider(unittest.TestCase):
    """المزوّد فوق PydanticAI."""

    def test_agent_output_becomes_provider_response(self) -> None:
        from pydantic_ai import Agent
        from pydantic_ai.models.test import TestModel

        agent = Agent(model=TestModel(custom_output_text="نتيجة"))
        provider = PydanticAIProvider(name="test", agent=agent)
        response = provider.complete(
            CompletionRequest(capability="media.render", prompt="س"), PROFILE
        )
        self.assertEqual(response.text, "نتيجة")
        self.assertGreaterEqual(response.tokens_out, 0)

    def test_fallback_model_replaces_failed_primary(self) -> None:
        from pydantic_ai import Agent
        from pydantic_ai.exceptions import ModelAPIError
        from pydantic_ai.models.fallback import FallbackModel
        from pydantic_ai.models.function import FunctionModel
        from pydantic_ai.models.test import TestModel

        def failing(messages, info):
            raise ModelAPIError(model_name="failing-model", message="فشل مقصود")

        agent = Agent(
            model=FallbackModel(
                FunctionModel(failing),
                TestModel(custom_output_text="احتياطي"),
            )
        )
        provider = PydanticAIProvider(name="test", agent=agent)
        response = provider.complete(
            CompletionRequest(capability="media.render", prompt="س"), PROFILE
        )
        self.assertEqual(response.text, "احتياطي")

    def test_agent_without_key_is_refused_at_build_time(self) -> None:
        import os

        os.environ.pop("DEEPSEEK_API_KEY", None)
        with self.assertRaises(AgentLayerError):
            build_deepseek_agent()

    def test_provider_without_agent_raises_clear_error(self) -> None:
        provider = PydanticAIProvider(name="test", agent=None)
        with self.assertRaises(Exception):
            provider.complete(
                CompletionRequest(capability="media.render", prompt="س"), PROFILE
            )


if __name__ == "__main__":
    unittest.main()
