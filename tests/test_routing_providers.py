"""اختبارات مزوّدَي OpenRouter وGroq — مع خادم HTTP محلي حقيقي.

لا شبكة في الاختبار: الخادم المحلي يستقبل الجسم فعلاً فنتحقّق أن
`extra_body` وصل إلى المزوّد كما هو، وأن النماذج المستعملة في القوائم
هي وحدها المسموحة بسعر معروف.
"""

from __future__ import annotations

import json
import os
import threading
import unittest

from maestro.routing.base import CompletionRequest, ModelProfile, with_extra_body
from maestro.routing.groq import (
    GROQ_MODEL_PRICES,
    groq_arabic_profile,
    groq_fast_profile,
    groq_profile,
    groq_quality_profile,
)
from maestro.routing.http_provider import OpenAICompatibleProvider, ProviderError
from maestro.routing.openrouter import openrouter_deepseek_profile

from tests.test_http_provider import _Handler, _Server


class _LocalCase(unittest.TestCase):
    """خادم محلي لكل اختبار."""

    def setUp(self) -> None:
        _Handler.received = []
        _Handler.status_code = 200
        _Handler.payload = {
            "id": "chat-1",
            "model": "m",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "نتيجة"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        self.server = _Server(("127.0.0.1", 0), _Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}/v1"
        os.environ["MAESTRO_TEST_KEY"] = "test-key"
        self.addCleanup(os.environ.pop, "MAESTRO_TEST_KEY", None)
        self.provider = OpenAICompatibleProvider(name="api")


class TestExtraBody(_LocalCase):
    """الجسم الإضافي في الطلب."""

    def _profile(self, extra_body: str = "") -> ModelProfile:
        return ModelProfile(
            name="api",
            tier="api",
            model="m",
            cost_in_per_mtok=0.1,
            cost_out_per_mtok=0.2,
            max_context=1000,
            api_key_env="MAESTRO_TEST_KEY",
            base_url=self.base_url,
            extra_body=extra_body,
        )

    def test_extra_body_is_merged_into_request(self) -> None:
        profile = with_extra_body(self._profile(), {"reasoning": {"effort": "low"}})
        self.provider.complete(CompletionRequest(capability="c", prompt="س"), profile)
        body = _Handler.received[0]["body"]
        self.assertEqual(body["reasoning"], {"effort": "low"})
        self.assertEqual(body["model"], "m")

    def test_empty_extra_body_leaves_payload_unchanged(self) -> None:
        self.provider.complete(CompletionRequest(capability="c", prompt="س"), self._profile())
        body = _Handler.received[0]["body"]
        self.assertNotIn("reasoning", body)

    def test_invalid_extra_body_raises_before_request(self) -> None:
        with self.assertRaises(ProviderError):
            self.provider.complete(
                CompletionRequest(capability="c", prompt="س"), self._profile("ليس JSON")
            )
        self.assertEqual(_Handler.received, [])

    def test_reasoning_only_reply_reports_the_real_cause(self) -> None:
        _Handler.payload = {
            "choices": [{"message": {"content": None, "reasoning": "خطوتان..."}}],
            "usage": {},
        }
        profile = with_extra_body(self._profile(), {"reasoning": {"effort": "low"}})
        with self.assertRaises(ProviderError) as caught:
            self.provider.complete(CompletionRequest(capability="c", prompt="س"), profile)
        self.assertIn("reasoning", str(caught.exception))


class TestOpenRouterProfile(unittest.TestCase):
    """بطاقة OpenRouter."""

    def test_prices_come_from_the_openrouter_api(self) -> None:
        profile = openrouter_deepseek_profile()
        self.assertEqual(profile.cost_in_per_mtok, 0.036)
        self.assertEqual(profile.cost_out_per_mtok, 0.50)
        self.assertEqual(profile.max_context, 1_048_576)

    def test_model_and_key_env(self) -> None:
        profile = openrouter_deepseek_profile()
        self.assertEqual(profile.model, "deepseek/deepseek-v4.1-flash-1017")
        self.assertEqual(profile.api_key_env, "OPENROUTER_API_KEY")
        self.assertEqual(profile.base_url, "https://openrouter.ai/api/v1")

    def test_reasoning_effort_is_low_by_default(self) -> None:
        profile = openrouter_deepseek_profile()
        self.assertEqual(json.loads(profile.extra_body), {"reasoning": {"effort": "low"}})

    def test_reasoning_effort_can_be_dropped(self) -> None:
        profile = openrouter_deepseek_profile(reasoning_effort=None)
        self.assertEqual(profile.extra_body, "")

    def test_cost_estimate_uses_profile_prices(self) -> None:
        profile = openrouter_deepseek_profile()
        # 1000 رمز داخل و 500 خارج
        expected = 1000 / 1e6 * 0.036 + 500 / 1e6 * 0.50
        self.assertAlmostEqual(profile.estimate_cost(1000, 500), expected)


class TestGroqProfiles(unittest.TestCase):
    """بطاقات Groq."""

    def test_every_known_model_has_a_price(self) -> None:
        for model, (cost_in, cost_out, context) in GROQ_MODEL_PRICES.items():
            with self.subTest(model=model):
                profile = groq_profile(model=model)
                self.assertEqual(profile.cost_in_per_mtok, cost_in)
                self.assertEqual(profile.cost_out_per_mtok, cost_out)
                self.assertEqual(profile.max_context, context)

    def test_named_helpers_pick_the_right_models(self) -> None:
        self.assertEqual(groq_fast_profile().model, "openai/gpt-oss-20b")
        self.assertEqual(groq_quality_profile().model, "openai/gpt-oss-120b")
        self.assertEqual(groq_arabic_profile().model, "qwen/qwen3.8-27b")

    def test_unknown_model_raises_instead_of_guessing_a_price(self) -> None:
        with self.assertRaises(ValueError) as caught:
            groq_profile(model="some/unknown-model")
        self.assertIn("GROQ_MODEL_PRICES", str(caught.exception))

    def test_key_env_and_base_url(self) -> None:
        profile = groq_profile()
        self.assertEqual(profile.api_key_env, "GROQ_API_KEY")
        self.assertEqual(profile.base_url, "https://api.groq.com/openai/v1")


if __name__ == "__main__":
    unittest.main()
