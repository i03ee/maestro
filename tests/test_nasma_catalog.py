"""اختبارات تكامل نَسمة: من ملف مورّد إلى كتالوج منشور."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from maestro.durable.journal import DurableJournal
from maestro.durable.runner import DurableRunner
from maestro.guards.budget import BudgetGuard
from maestro.guards.permission import PermissionGuard
from maestro.integrations.nasma.catalog import (
    LOCALES,
    format_iqd,
    load_supplier_rows,
    product_from_row,
    safe_image,
    validate_product,
)
from maestro.integrations.nasma.pipeline import (
    build_product_task,
    default_registry,
    run_catalog,
    write_catalog,
)
from maestro.integrations.nasma.prompts import ModelContractError, parse_response
from maestro.routing.base import CompletionResponse, ModelProfile, RoutingPolicy
from maestro.routing.offline import ScriptedProvider
from maestro.routing.router import ModelRouter
from maestro.runtime.runner import CapabilityRunner

GOLDEN = Path(__file__).parent / "golden"

PROFILE = ModelProfile(
    name="local",
    tier="local",
    model="test-model",
    cost_in_per_mtok=0.0,
    cost_out_per_mtok=0.0,
    max_context=8192,
)


def _valid_reply(product_id: str) -> str:
    return json.dumps(
        {
            "id": product_id,
            "name": {"ar": "اسم", "ku": "ناو", "en": "Name"},
            "tag": {"ar": "وسم", "ku": "تاگ", "en": "Tag"},
            "description": {"ar": "وصف", "ku": ".description", "en": "Description"},
        },
        ensure_ascii=False,
    )


class TestCatalogRules(unittest.TestCase):
    """قواعد شكل المنتج (نفسها في نَسمة)."""

    def test_iqd_format_uses_arabic_indic_digits(self) -> None:
        self.assertEqual(format_iqd(28000, "ar"), "٢٨٬٠٠٠ د.ع")
        self.assertEqual(format_iqd(12500, "ku"), "١٢٬٥٠٠ د.ع")
        self.assertEqual(format_iqd(28000, "en"), "28,000 IQD")

    def test_negative_price_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            format_iqd(-1, "ar")

    def test_unsafe_image_is_rejected(self) -> None:
        self.assertIsNone(safe_image("javascript:alert(1)"))
        self.assertIsNone(safe_image("data:text/html;base64,xxx"))
        self.assertEqual(
            safe_image("https://cdn.example.com/a.jpg"), "https://cdn.example.com/a.jpg"
        )

    def test_three_locales_are_supported(self) -> None:
        self.assertEqual(LOCALES, ("ar", "ku", "en"))


class TestProductValidation(unittest.TestCase):
    """فحص المنتج قبل أي استدعاء نموذج."""

    def _product(self, **overrides):
        row = {
            "id": "sku-1",
            "name_ar": "اسم",
            "name_ku": "ناو",
            "name_en": "Name",
            "category_ar": "تصنيف",
            "category_ku": "پۆل",
            "category_en": "Category",
            "price": "1000",
            "slug": "sku-1",
        }
        row.update(overrides)
        return product_from_row(row)

    def test_valid_product_passes(self) -> None:
        self.assertEqual(validate_product(self._product()), [])

    def test_missing_locale_is_reported(self) -> None:
        product = self._product(name_ku="")
        problems = validate_product(product)
        self.assertTrue(any("ku" in problem for problem in problems))

    def test_negative_price_is_reported(self) -> None:
        problems = validate_product(self._product(price="-5"))
        self.assertTrue(any("السعر" in problem for problem in problems))

    def test_unsafe_image_is_dropped_and_reported(self) -> None:
        product = self._product(image="javascript:alert(1)")
        self.assertIsNone(product.image)
        self.assertEqual(validate_product(product), [])


class TestModelContract(unittest.TestCase):
    """عقد الردّ صارم."""

    def setUp(self) -> None:
        self.product = product_from_row(
            {
                "id": "sku-1",
                "name_ar": "اسم",
                "name_ku": "ناو",
                "name_en": "Name",
                "category_ar": "تصنيف",
                "category_ku": "پۆل",
                "category_en": "Category",
                "price": "1000",
                "slug": "sku-1",
            }
        )

    def test_valid_reply_parses(self) -> None:
        parsed = parse_response(_valid_reply("sku-1"), self.product)
        self.assertEqual(parsed["name"]["ar"], "اسم")

    def test_non_json_reply_is_rejected(self) -> None:
        with self.assertRaises(ModelContractError):
            parse_response("نص حرّ", self.product)

    def test_missing_locale_in_reply_is_rejected(self) -> None:
        reply = json.loads(_valid_reply("sku-1"))
        del reply["name"]["ku"]
        with self.assertRaises(ModelContractError):
            parse_response(json.dumps(reply, ensure_ascii=False), self.product)

    def test_wrong_product_id_is_rejected(self) -> None:
        with self.assertRaises(ModelContractError):
            parse_response(_valid_reply("sku-999"), self.product)

    def test_fenced_json_is_accepted(self) -> None:
        parsed = parse_response("```json\n" + _valid_reply("sku-1") + "\n```", self.product)
        self.assertEqual(parsed["id"], "sku-1")


class TestCatalogPipeline(unittest.TestCase):
    """المسار كاملاً."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.rows = load_supplier_rows(GOLDEN / "supplier_rows.json")
        self.provider = ScriptedProvider(
            "local",
            [
                CompletionResponse(
                    text=_valid_reply("sku-001"), tokens_in=50, tokens_out=80, model="test-model"
                ),
                CompletionResponse(
                    text=_valid_reply("sku-002"), tokens_in=50, tokens_out=80, model="test-model"
                ),
            ],
        )
        router = ModelRouter(
            providers={"local": self.provider},
            profiles={"local": PROFILE},
            policy=RoutingPolicy(),
            budget=BudgetGuard(max_cost_usd=5.0, max_tokens=200_000),
        )
        registry = default_registry()
        capability_runner = CapabilityRunner(
            registry,
            router,
            PermissionGuard(allowed_capabilities=frozenset({"catalog.ingest"}), max_authority=2),
        )
        self.journal = DurableJournal(Path(self._tmp.name) / "journal.jsonl")
        self.runner = DurableRunner(capability_runner, self.journal)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_invalid_row_is_rejected_before_the_model(self) -> None:
        result = run_catalog(self.rows, self.runner)
        rejected_ids = [product_id for product_id, _ in result.rejected]
        self.assertIn("sku-003", rejected_ids)
        problems = dict(result.rejected)["sku-003"]
        self.assertTrue(any("السعر" in problem for problem in problems))
        # منتجان فقط يستدعيان النموذج
        self.assertEqual(len(self.provider.calls), 2)

    def test_valid_products_are_published_with_model_text(self) -> None:
        result = run_catalog(self.rows, self.runner)
        published = {product.id: product for product in result.products}
        self.assertEqual(set(published), {"sku-001", "sku-002"})
        self.assertEqual(published["sku-001"].names["ar"], "اسم")
        self.assertEqual(published["sku-001"].tags["ku"], "تاگ")

    def test_each_product_is_a_separate_task(self) -> None:
        run_catalog(self.rows, self.runner)
        tasks = {record.task_id for record in self.journal.records()}
        self.assertIn("catalog:sku-001", tasks)
        self.assertIn("catalog:sku-002", tasks)

    def test_rerun_does_not_call_the_model_again(self) -> None:
        run_catalog(self.rows, self.runner)
        calls_after_first = len(self.provider.calls)
        run_catalog(self.rows, self.runner)
        self.assertEqual(len(self.provider.calls), calls_after_first)

    def test_contract_violation_rejects_the_product_only(self) -> None:
        self.provider.script[0] = CompletionResponse(
            text="نص حرّ", tokens_in=5, tokens_out=5, model="test-model"
        )
        result = run_catalog(self.rows, self.runner)
        rejected_ids = [product_id for product_id, _ in result.rejected]
        self.assertIn("sku-001", rejected_ids)
        self.assertNotIn("sku-002", rejected_ids)
        self.assertEqual(len(result.products), 1)

    def test_written_catalog_matches_nasma_shape(self) -> None:
        result = run_catalog(self.rows, self.runner)
        path = write_catalog(result, Path(self._tmp.name) / "catalog.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("products", payload)
        self.assertIn("rejected", payload)
        entry = payload["products"][0]
        for key in ("id", "name", "category", "price", "slug", "image", "imageAlt", "tag", "tone"):
            self.assertIn(key, entry)


class TestTaskDocument(unittest.TestCase):
    """مستند المهمة."""

    def test_task_is_critical_with_ensemble_and_evidence(self) -> None:
        product = product_from_row(
            {
                "id": "sku-1",
                "name_ar": "اسم",
                "name_ku": "ناو",
                "name_en": "Name",
                "category_ar": "تصنيف",
                "category_ku": "پۆل",
                "category_en": "Category",
                "price": "1000",
                "slug": "sku-1",
            }
        )
        task = build_product_task(product)
        self.assertTrue(task["critical"])
        self.assertEqual(task["redundancy"]["min_agreement"], 2)
        self.assertTrue(task["evidence"]["required"])
        self.assertEqual(len(task["steps"]), 2)


if __name__ == "__main__":
    unittest.main()
