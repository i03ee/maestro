"""اختبارات المزوّد الحقيقي: خادم HTTP محلي حقيقي، لا محاكاة."""

from __future__ import annotations

import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from maestro.routing.base import CompletionRequest, ModelProfile
from maestro.routing.deepseek import deepseek_fallback_profile, deepseek_flash_profile
from maestro.routing.http_provider import (
    MissingCredentials,
    OpenAICompatibleProvider,
    ProviderError,
)


class _Handler(BaseHTTPRequestHandler):
    """خادم اختبار يردّ بردّ OpenAI-style."""

    payload: dict = {}
    status_code: int = 200
    received: list[dict] = []

    def do_POST(self) -> None:  # noqa: N802 — اسم الطريق في المكتبة القياسية
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        type(self).received.append(
            {"path": self.path, "body": json.loads(raw.decode("utf-8")), "headers": dict(self.headers)}
        )
        body = json.dumps(type(self).payload).encode("utf-8")
        self.send_response(type(self).status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # noqa: A003 — كتم السجل
        return


class HttpProviderCase(unittest.TestCase):
    """خادم محلي لكل اختبار."""

    def setUp(self) -> None:
        _Handler.received = []
        _Handler.status_code = 200
        _Handler.payload = {
            "id": "chat-1",
            "model": "deepseek-flash",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "نتيجة"}}],
            "usage": {"prompt_tokens": 120, "completion_tokens": 45},
        }
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}/v1"
        self.profile = ModelProfile(
            name="api",
            tier="api",
            model="deepseek-flash",
            cost_in_per_mtok=0.15,
            cost_out_per_mtok=0.60,
            max_context=1_000_000,
            api_key_env="MAESTRO_TEST_KEY",
            base_url=self.base_url,
        )
        self.provider = OpenAICompatibleProvider(name="api")

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def _with_key(self):
        os.environ["MAESTRO_TEST_KEY"] = "test-key"
        self.addCleanup(os.environ.pop, "MAESTRO_TEST_KEY", None)


class TestRequestShape(HttpProviderCase):
    """شكل الطلب: هو OpenAI-compatible فعلاً."""

    def test_request_targets_chat_completions(self) -> None:
        self._with_key()
        self.provider.complete(
            CompletionRequest(capability="media.render", prompt="مرحبا"), self.profile
        )
        self.assertEqual(_Handler.received[0]["path"], "/v1/chat/completions")

    def test_request_body_matches_openai_schema(self) -> None:
        self._with_key()
        self.provider.complete(
            CompletionRequest(capability="media.render", prompt="مرحبا", max_output_tokens=256),
            self.profile,
        )
        body = _Handler.received[0]["body"]
        self.assertEqual(body["model"], "deepseek-flash")
        self.assertEqual(body["max_tokens"], 256)
        self.assertEqual(body["messages"][0]["role"], "user")
        self.assertEqual(body["messages"][0]["content"], "مرحبا")

    def test_authorization_header_is_sent(self) -> None:
        self._with_key()
        self.provider.complete(
            CompletionRequest(capability="media.render", prompt="س"), self.profile
        )
        headers = {k.lower(): v for k, v in _Handler.received[0]["headers"].items()}
        self.assertEqual(headers.get("authorization"), "Bearer test-key")


class TestResponseParsing(HttpProviderCase):
    """تحليل الردّ وحساب التكلفة."""

    def test_response_is_normalised(self) -> None:
        self._with_key()
        response = self.provider.complete(
            CompletionRequest(capability="media.render", prompt="س"), self.profile
        )
        self.assertEqual(response.text, "نتيجة")
        self.assertEqual(response.tokens_in, 120)
        self.assertEqual(response.tokens_out, 45)
        self.assertEqual(response.model, "deepseek-flash")

    def test_cost_is_computed_from_profile(self) -> None:
        self._with_key()
        response = self.provider.complete(
            CompletionRequest(capability="media.render", prompt="س"), self.profile
        )
        expected = 120 / 1e6 * 0.15 + 45 / 1e6 * 0.60
        self.assertAlmostEqual(self.profile.estimate_cost(response.tokens_in, response.tokens_out), expected)


class TestFailureModes(HttpProviderCase):
    """كل فشل يُبلَّغ، ولا يُختبَر."""

    def test_missing_key_raises_before_any_request(self) -> None:
        os.environ.pop("MAESTRO_TEST_KEY", None)
        with self.assertRaises(MissingCredentials):
            self.provider.complete(
                CompletionRequest(capability="media.render", prompt="س"), self.profile
            )
        self.assertEqual(_Handler.received, [])

    def test_server_error_raises_provider_error(self) -> None:
        self._with_key()
        _Handler.status_code = 500
        with self.assertRaises(ProviderError):
            self.provider.complete(
                CompletionRequest(capability="media.render", prompt="س"), self.profile
            )

    def test_non_json_body_raises(self) -> None:
        self._with_key()
        _Handler.payload = {"choices": []}
        with self.assertRaises(ProviderError):
            self.provider.complete(
                CompletionRequest(capability="media.render", prompt="س"), self.profile
            )

    def test_missing_content_raises(self) -> None:
        self._with_key()
        _Handler.payload = {"choices": [{"message": {}}], "usage": {}}
        with self.assertRaises(ProviderError):
            self.provider.complete(
                CompletionRequest(capability="media.render", prompt="س"), self.profile
            )

    def test_unreachable_endpoint_raises(self) -> None:
        self._with_key()
        broken = ModelProfile(
            name="api",
            tier="api",
            model="m",
            cost_in_per_mtok=0.0,
            cost_out_per_mtok=0.0,
            max_context=1000,
            api_key_env="MAESTRO_TEST_KEY",
            base_url="http://127.0.0.1:9/v1",
        )
        with self.assertRaises(ProviderError):
            self.provider.complete(
                CompletionRequest(capability="media.render", prompt="س"), broken
            )


class TestDeepSeekProfile(unittest.TestCase):
    """بطاقات DeepSeek."""

    def test_off_peak_prices(self) -> None:
        profile = deepseek_flash_profile(off_peak=True)
        self.assertEqual(profile.cost_in_per_mtok, 0.15)
        self.assertEqual(profile.cost_out_per_mtok, 0.60)
        self.assertEqual(profile.max_context, 1_000_000)
        self.assertEqual(profile.api_key_env, "DEEPSEEK_API_KEY")

    def test_peak_prices(self) -> None:
        profile = deepseek_flash_profile(off_peak=False)
        self.assertEqual(profile.cost_in_per_mtok, 0.30)
        self.assertEqual(profile.cost_out_per_mtok, 1.20)

    def test_fallback_profile_is_cheaper_tier(self) -> None:
        profile = deepseek_fallback_profile()
        self.assertEqual(profile.tier, "fallback")
        self.assertEqual(profile.model, "deepseek-chat")


if __name__ == "__main__":
    unittest.main()
