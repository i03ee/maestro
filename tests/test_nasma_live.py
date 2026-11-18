"""اختبارات المسار الحيّ لنَسمة: السياق، وسقف الإخراج، والرفض بسبب مكتوب.

المسار الحيّ يمرّ على: مستند IR ← حارس الصلاحية ← حارس الميزانية ← التنفيذ
المتين ← الموجّه ← النموذج. هنا نثبت **الحدود** التي تكسر الطريق:
- مطالبة بلا بيانات ⇒ النموذج يخترع (ولذلك السياق إلزامي).
- سقف إخراج صغير ⇒ الردّ ينقطع.
- سعر غير صالح ⇒ المنتج مرفوض بسبب مكتوب، والبقية تُنشر.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from maestro.durable.journal import DurableJournal
from maestro.durable.runner import DurableRunner
from maestro.evidence.log import EvidenceLog
from maestro.guards.budget import BudgetGuard
from maestro.guards.permission import PermissionGuard
from maestro.integrations.nasma.catalog import load_supplier_rows
from maestro.integrations.nasma.pipeline import (
    build_product_task,
    default_registry,
    run_catalog,
)
from maestro.integrations.nasma.prompts import CONTRACT_PROMPT_AR
from maestro.routing.base import CompletionResponse, ModelProfile
from maestro.routing.offline import ScriptedProvider
from maestro.routing.router import ModelRouter
from maestro.runtime.runner import CapabilityRunner

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden" / "supplier_rows.json"

CARD = {
    "id": "sku-001",
    "name": {"ar": "سيروم", "ku": "سیرەم", "en": "Serum"},
    "tag": {"ar": "عناية", "ku": "چاودێری", "en": "Care"},
    "description": {"ar": "وصف", "ku": "پێناسە", "en": "Description"},
}


def _runner(script: list, out_dir: Path) -> DurableRunner:
    provider = ScriptedProvider(name="test", script=script)
    profile = ModelProfile(
        name="test",
        tier="api",
        model="test-model",
        cost_in_per_mtok=0.036,
        cost_out_per_mtok=0.50,
        max_context=100_000,
        api_key_env=None,
        base_url="http://127.0.0.1:9/v1",
    )
    router = ModelRouter(
        providers={"test": provider},
        profiles={"test": profile},
        budget=BudgetGuard(max_cost_usd=5.0, max_tokens=500_000),
    )
    permissions = PermissionGuard(
        allowed_capabilities=frozenset({"catalog.ingest"}), max_authority=2
    )
    capability_runner = CapabilityRunner(
        default_registry(), router, permissions, EvidenceLog(out_dir / "evidence.jsonl")
    )
    return DurableRunner(capability_runner, DurableJournal(out_dir / "journal.jsonl"))


class TestPromptCarriesTheProduct(unittest.TestCase):
    """المطالبة تحمل العقد والبيانات."""

    def test_template_contains_the_contract_and_a_context_slot(self) -> None:
        spec = default_registry().get("catalog.ingest")
        self.assertIn("{context}", spec.prompt_template_ar)
        self.assertIn("{intent}", spec.prompt_template_ar)
        self.assertIn("JSON", spec.prompt_template_ar)
        self.assertIn("نَسمة", spec.prompt_template_ar)

    def test_rendered_prompt_contains_the_product_data(self) -> None:
        spec = default_registry().get("catalog.ingest")
        prompt = spec.render_prompt("حرّر بطاقة المنتج", json.dumps({"id": "sku-001"}))
        self.assertIn("sku-001", prompt)
        self.assertIn("حرّر بطاقة المنتج", prompt)

    def test_contract_text_alone_survives_brace_substitution(self) -> None:
        spec = default_registry().get("catalog.ingest")
        prompt = spec.render_prompt("نيّة", "سياق")
        self.assertIn('"name"', prompt)
        self.assertNotIn("{context}", prompt)
        self.assertNotIn("{intent}", prompt)

    def test_contract_prompt_is_valid_json_example(self) -> None:
        self.assertIn('"description"', CONTRACT_PROMPT_AR)
        self.assertIn("ar", CONTRACT_PROMPT_AR)


class TestTaskBudget(unittest.TestCase):
    """ميزانية المهمة."""

    def test_task_declares_explicit_output_tokens(self) -> None:
        rows = load_supplier_rows(GOLDEN)
        from maestro.integrations.nasma.catalog import product_from_row

        task = build_product_task(product_from_row(rows[0]))
        budget = task["budget"]
        self.assertGreaterEqual(budget["max_output_tokens"], 4000)
        self.assertEqual(task["redundancy"]["min_agreement"], 2)

    def test_output_cap_is_not_the_default_1024(self) -> None:
        rows = load_supplier_rows(GOLDEN)
        from maestro.integrations.nasma.catalog import product_from_row

        task = build_product_task(product_from_row(rows[0]))
        default_output = min(1024, task["budget"]["max_tokens"])
        self.assertGreater(task["budget"]["max_output_tokens"], default_output)


class TestLiveCatalog(unittest.TestCase):
    """التشغيل الحيّ للكتالوج."""

    def test_publishes_valid_products_and_rejects_the_invalid_one(self) -> None:
        rows = load_supplier_rows(GOLDEN)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            card_two = json.loads(json.dumps(CARD))
            card_two["id"] = "sku-002"
            runner = _runner(
                [
                    CompletionResponse(
                        text=json.dumps(CARD, ensure_ascii=False),
                        tokens_in=100,
                        tokens_out=200,
                        model="m",
                    ),
                    CompletionResponse(
                        text=json.dumps(card_two, ensure_ascii=False),
                        tokens_in=100,
                        tokens_out=200,
                        model="m",
                    ),
                ],
                out,
            )
            result = run_catalog(rows, runner, task_id="catalog")
            published = {product.id for product in result.products}
            rejected = dict(result.rejected)
            self.assertIn("sku-001", published)
            self.assertIn("sku-002", published)
            self.assertIn("sku-003", rejected)
            self.assertTrue(rejected["sku-003"])

    def test_contract_violation_rejects_the_product_only(self) -> None:
        broken = json.loads(json.dumps(CARD))
        broken["name"]["ku"] = ""
        rows = load_supplier_rows(GOLDEN)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            runner = _runner(
                [
                    CompletionResponse(
                        text=json.dumps(broken, ensure_ascii=False),
                        tokens_in=10,
                        tokens_out=20,
                        model="m",
                    )
                ],
                out,
            )
            result = run_catalog(rows, runner, task_id="catalog")
            self.assertEqual(result.products, ())
            self.assertTrue(result.rejected)

    def test_journal_records_every_product_task(self) -> None:
        rows = load_supplier_rows(GOLDEN)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            runner = _runner(
                [
                    CompletionResponse(
                        text=json.dumps(CARD, ensure_ascii=False),
                        tokens_in=10,
                        tokens_out=20,
                        model="m",
                    )
                ],
                out,
            )
            run_catalog(rows, runner, task_id="catalog")
            journal = out / "journal.jsonl"
            self.assertTrue(journal.is_file())
            events = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
            keys = {event.get("idempotency_key") for event in events}
            self.assertIn("catalog:sku-001", keys)


if __name__ == "__main__":
    unittest.main()
