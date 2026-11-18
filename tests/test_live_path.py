"""اختبارات المسار الحيّ — بمزوّد حتمي (لا شبكة) وخادم محلي حقيقي.

المسار الحيّ حقيقي في التشغيل، لكن اختباره **حتمي**: مزوّد `ScriptedProvider`
يعيد ردوداً مُعدّة، فنتأكّد أن:
- المطالبات تُبنى وتُرسَل كما هي.
- الردّ المخالف للعقد **لا يُنتج artefact**.
- التكلفة والزمن يُسجَّلان في التقرير.
- فحص الروابط يفحص فعلاً (خادم محلي) ويكشف «غير معروف» وURL ميت.
"""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from maestro.producers.live import MAX_OUTPUT_TOKENS, run_live
from maestro.producers.prompts import (
    PROMPT_BUILDERS,
    candidates_prompt,
    competitors_prompt,
    prd_prompt,
)
from maestro.producers.structured import StructuredResponseError
from maestro.routing.base import CompletionResponse, ModelProfile
from maestro.routing.offline import ScriptedProvider
from maestro.routing.router import ModelRouter

GOOD_PRD = {
    "product_name": "نَسمة",
    "problem": "صعوبة إيجاد منتجات عناية موثوقة بأسعار واضحة.",
    "features": [
        {
            "id": "F1",
            "title": "تسجيل الدخول",
            "priority": "must",
            "story": "كـمستخدم أريد إنشاء حساب كي أحفظ طلباتي.",
            "criteria": ["يكتمل إنشاء الحساب ببريد وكلمة مرور."],
        }
    ],
}

GOOD_COMPETITORS = {
    "competitors": [
        {
            "name": "متجر",
            "url": "https://example.com",
            "strengths": "قوة",
            "weaknesses": "ضعف",
            "price_point": "متوسط",
            "source": "صفحة الأسعار الرسمية",
        },
        {
            "name": "متجر آخر",
            "url": "https://example.org",
            "strengths": "قوة",
            "weaknesses": "ضعف",
            "price_point": "غير معروف",
            "source": "صفحة المنتجات",
        },
        {
            "name": "متجر ثالث",
            "url": "https://example.net",
            "strengths": "قوة",
            "weaknesses": "ضعف",
            "price_point": "مرتفع",
            "source": "إعلان معلن",
        },
    ]
}

GOOD_CANDIDATES = {
    "candidates": [
        {
            "name": "Meilisearch",
            "source": "https://github.com/meilisearch/meilisearch",
            "spdx": "MIT",
            "scan_result": "clean",
            "decision": "allow",
            "reason": "ترخيص MIT متوافق.",
        }
    ]
}


def _profile(name: str = "test") -> ModelProfile:
    return ModelProfile(
        name=name,
        tier="api",
        model="test-model",
        cost_in_per_mtok=0.036,
        cost_out_per_mtok=0.50,
        max_context=100_000,
        api_key_env=None,
        base_url="http://127.0.0.1:9/v1",
    )


def _router(script: list) -> tuple[ModelRouter, ScriptedProvider]:
    provider = ScriptedProvider(name="test", script=script)
    router = ModelRouter(
        providers={"test": provider},
        profiles={"test": _profile()},
    )
    return router, provider


class TestPrompts(unittest.TestCase):
    """المطالبات."""

    def test_every_capability_has_a_prompt_and_a_validator(self) -> None:
        self.assertEqual(
            sorted(PROMPT_BUILDERS),
            ["idea.prd", "research.candidates", "research.competitors"],
        )
        for builder, validator in PROMPT_BUILDERS.values():
            with self.subTest(builder=builder.__name__):
                text = builder({"idea": "فكرة", "market": "سوق", "need": "حاجة"})
                self.assertIn("JSON", text)
                self.assertEqual(validator({}), validator({}))  # يفحص بلا خطأ

    def test_prd_prompt_states_the_priority_vocabulary(self) -> None:
        text = prd_prompt({"idea": "منصة تجارة"})
        self.assertIn("must", text)
        self.assertIn("معايير قبول", text)

    def test_competitors_prompt_demands_a_source_per_row(self) -> None:
        text = competitors_prompt({"market": "تجارة الجمال العراق"})
        self.assertIn("مصدر", text)
        self.assertIn("غير معروف", text)

    def test_candidates_prompt_states_the_licence_rule(self) -> None:
        text = candidates_prompt({"need": "فهرسة"})
        self.assertIn("allow", text)
        self.assertIn("deny", text)


class TestLiveRun(unittest.TestCase):
    """التشغيل الحيّ بمزوّد حتمي."""

    def test_prd_produces_artefacts(self) -> None:
        router, provider = _router(
            [
                CompletionResponse(
                    text=json.dumps(GOOD_PRD, ensure_ascii=False),
                    tokens_in=120,
                    tokens_out=340,
                    model="test-model",
                )
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            outcome = run_live(router, "idea.prd", {"idea": "فكرة"}, tmp)
            root = Path(tmp)
            self.assertTrue((root / "artifacts" / "prd.md").is_file())
            self.assertTrue((root / "artifacts" / "user_stories.json").is_file())
            self.assertEqual(outcome.provider, "test")
            self.assertEqual(outcome.tokens_out, 340)
            self.assertAlmostEqual(outcome.cost_usd, 120 / 1e6 * 0.036 + 340 / 1e6 * 0.50)
            self.assertGreaterEqual(len(outcome.artefacts), 2)
        self.assertEqual(provider.calls[0].capability, "idea.prd")
        self.assertEqual(provider.calls[0].max_output_tokens, MAX_OUTPUT_TOKENS["idea.prd"])

    def test_contract_violation_produces_no_artefact(self) -> None:
        broken = json.loads(json.dumps(GOOD_PRD))
        broken["features"] = []
        router, _ = _router(
            [CompletionResponse(text=json.dumps(broken), tokens_in=10, tokens_out=10, model="m")]
        )
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(StructuredResponseError):
                run_live(router, "idea.prd", {"idea": "فكرة"}, tmp)
            self.assertFalse((Path(tmp) / "artifacts" / "prd.md").exists())

    def test_non_json_reply_produces_no_artefact(self) -> None:
        router, _ = _router(
            [CompletionResponse(text="عذراً، لا أستطيع", tokens_in=5, tokens_out=5, model="m")]
        )
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(StructuredResponseError):
                run_live(router, "research.competitors", {"market": "سوق"}, tmp)

    def test_competitors_and_candidates_write_their_artefacts(self) -> None:
        router, _ = _router(
            [
                CompletionResponse(
                    text=json.dumps(GOOD_COMPETITORS, ensure_ascii=False),
                    tokens_in=50,
                    tokens_out=90,
                    model="m",
                )
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            run_live(router, "research.competitors", {"market": "سوق"}, tmp)
            self.assertTrue((Path(tmp) / "artifacts" / "market" / "competitor_matrix.csv").is_file())

        router, _ = _router(
            [
                CompletionResponse(
                    text=json.dumps(GOOD_CANDIDATES, ensure_ascii=False),
                    tokens_in=30,
                    tokens_out=40,
                    model="m",
                )
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            run_live(router, "research.candidates", {"need": "حاجة"}, tmp)
            self.assertTrue((Path(tmp) / "artifacts" / "research" / "candidates.jsonl").is_file())

    def test_unknown_capability_raises(self) -> None:
        router, _ = _router([])
        with self.assertRaises(ValueError):
            run_live(router, "does.not.exist", {}, "/tmp")

    def test_fallback_is_reported(self) -> None:
        failing = ScriptedProvider(name="first", script=[RuntimeError("تعذّر")])
        working = ScriptedProvider(
            name="second",
            script=[
                CompletionResponse(
                    text=json.dumps(GOOD_PRD, ensure_ascii=False),
                    tokens_in=10,
                    tokens_out=20,
                    model="m",
                )
            ],
        )
        router = ModelRouter(
            providers={"first": failing, "second": working},
            profiles={"first": _profile("first"), "second": _profile("second")},
        )
        with tempfile.TemporaryDirectory() as tmp:
            outcome = run_live(router, "idea.prd", {"idea": "فكرة"}, tmp)
            self.assertTrue(outcome.fallback_used)
            self.assertEqual(outcome.provider, "second")


class _Handler(BaseHTTPRequestHandler):
    """خادم محلي لفحص الروابط."""

    def do_GET(self) -> None:  # noqa: N802 — اسم الطريق في المكتبة القياسية
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args) -> None:  # noqa: A003 — كتم السجل
        return


class TestUrlCheck(unittest.TestCase):
    """فحص الروابط — يستدعي الدالة داخل السكربت."""

    def setUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.server.request_queue_size = 128
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def _check(self, matrix_text: str) -> list[dict]:
        import importlib.util
        import sys

        path = Path(__file__).resolve().parent.parent / "scripts" / "live_run.py"
        spec = importlib.util.spec_from_file_location("live_run_script", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            matrix = Path(tmp) / "competitor_matrix.csv"
            matrix.write_text(matrix_text, encoding="utf-8")
            return module.check_urls(matrix, timeout=5)

    def test_reachable_url_is_marked_as_responding(self) -> None:
        checks = self._check(
            "name,url,source\n"
            f"متجر,{self.base}/page,صفحة رسمية\n"
        )
        self.assertEqual(len(checks), 1)
        self.assertTrue(checks[0]["responded"])
        self.assertEqual(checks[0]["status"], 200)

    def test_non_url_text_is_flagged_not_crashed(self) -> None:
        checks = self._check("name,url,source\nمتجر,غير معروف,صفحة رسمية\n")
        self.assertEqual(checks[0]["detail"], "not_a_url")
        self.assertFalse(checks[0]["responded"])

    def test_dead_host_is_marked_as_not_responding(self) -> None:
        checks = self._check("name,url,source\nمتجر,http://127.0.0.1:9/x,صفحة\n")
        self.assertFalse(checks[0]["responded"])
        self.assertIsNone(checks[0]["status"])


if __name__ == "__main__":
    unittest.main()
