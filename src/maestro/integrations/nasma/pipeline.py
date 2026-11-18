"""مسار «بيانات المنتج»: من ملف مورّد إلى كتالوج نَسمة.

القدرة `catalog.ingest` حرجة: تُنفَّذ بتكرار نماذج ودليل إلزامي (IR-12 و
IR-13). المسار هنا يجهّز المهمة وينفّذها ويكتب المخرجات — والنموذج نفسه
يُستدعى عبر الموجّه، فتبقى البوابات واحدة لا اثنتين.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...durable.runner import DurableOutcome, DurableRunner
from ...runtime.registry import CapabilityRegistry
from ...runtime.runner import ExecutionReport
from ...runtime.spec import CapabilitySpec
from .catalog import NasmaProduct, product_from_row, validate_product
from .prompts import CONTRACT_PROMPT_AR, ModelContractError, build_prompt, parse_response

CAPABILITY = "catalog.ingest"


def default_registry() -> CapabilityRegistry:
    """سجل قدرات يتضمّن قدرة بيانات المنتج."""
    registry = CapabilityRegistry()
    registry.register(
        CapabilitySpec(
            name=CAPABILITY,
            description_ar="تحويل ملف مورّد إلى بطاقات منتجات بثلاث لغات",
            required_tools=("model.generate",),
            default_authority=2,
            critical=True,
            # العقد ثابت في القالب، وبيانات المنتج تأتي من `inputs` كسياق.
            prompt_template_ar=f"{CONTRACT_PROMPT_AR}\n\n{{intent}}\n\n{{context}}",
        )
    )
    return registry


@dataclass(frozen=True)
class CatalogRunResult:
    """نتيجة تشغيل مسار الكتالوج."""

    products: tuple[NasmaProduct, ...]
    rejected: tuple[tuple[str, tuple[str, ...]], ...]
    outcome: DurableOutcome | None = None
    report: ExecutionReport | None = None

    @property
    def ok(self) -> bool:
        return self.report is not None and self.report.ok

    def as_dict(self) -> dict[str, Any]:
        return {
            "products": [product.to_catalog_entry() for product in self.products],
            "rejected": [
                {"id": product_id, "problems": list(problems)}
                for product_id, problems in self.rejected
            ],
        }


def build_product_task(product: NasmaProduct) -> dict[str, Any]:
    """يبني مستند IR لمهمة منتج واحد (قدرة حرجة بتكرار ودليل).

    منتج واحد = مهمة واحدة = استدعاء نموذج واحد. هذا هو مبدأ «خطوات
    صغيرة»: نرفض تجميع عشرة منتجات في نداء واحد، لأن فشل واحد يُسقط
    البقية، والاستئناف يصير أضخم.
    """
    return {
        "ir_version": "1.0",
        "capability": CAPABILITY,
        "intent": (
            "تحرير بطاقة منتج واحد بثلاث لغات: " + product.names.get("ar", product.id)
        ),
        "authority": 2,
        "critical": True,
        "steps": [
            {
                "id": "s1",
                "agent": "catalog_writer",
                "action": "تحرير الاسم والوسم والوصف بكل لغة",
                "tools": ["model.generate"],
            },
            {
                "id": "s2",
                "agent": "catalog_verifier",
                "action": "التحقق من العقد ومن اكتمال اللغات",
                "tools": [],
            },
        ],
        "inputs": {"product": product.to_catalog_entry()},
        # max_output_tokens صريح: الافتراضي في المشغّل 1024 وهو أصغر من
        # ما تحتاجه بطاقة بثلاث لغات (قياس حيّ: الردّ انقطع عنده).
        "budget": {
            "max_tokens": 8_000,
            "max_output_tokens": 4_000,
            "max_cost_usd": 0.25,
            "max_wall_seconds": 120,
        },
        "redundancy": {"ensemble": ["local", "api", "fallback"], "min_agreement": 2},
        "evidence": {"required": True, "artifacts": ["catalog.json", "evidence.jsonl"]},
    }


def select_valid(products: list[NasmaProduct]) -> tuple[list[NasmaProduct], list[tuple[str, tuple[str, ...]]]]:
    """يفصل الصالح عن المرفوض بسبب مكتوب."""
    valid: list[NasmaProduct] = []
    rejected: list[tuple[str, tuple[str, ...]]] = []
    for product in products:
        problems = validate_product(product)
        if problems:
            rejected.append((product.id or "(بلا معرّف)", tuple(problems)))
        else:
            valid.append(product)
    return valid, rejected


def run_catalog(
    rows: list[dict[str, Any]],
    runner: DurableRunner,
    *,
    task_id: str = "catalog",
    idempotency_prefix: str | None = None,
) -> CatalogRunResult:
    """يشغّل المسار كاملاً: تصفية ← مهمة لكل منتج ← تنفيذ ← مخرجات.

    كل منتج مهمة مستقلة بمفتاح تكرارية خاص به: يُنفَّذ مرة واحدة، ويُستأنف
    منفرداً بعد انقطاع، ولا يُسقط فشل منتج بقية المنتجات.
    """
    products = [product_from_row(row) for row in rows]
    valid, rejected = select_valid(products)

    published: list[NasmaProduct] = []
    problems_by_id: list[tuple[str, tuple[str, ...]]] = list(rejected)
    outcome: DurableOutcome | None = None
    report: ExecutionReport | None = None

    for product in valid:
        task = build_product_task(product)
        product_task_id = f"{task_id}:{product.id}"
        key = f"{idempotency_prefix or task_id}:{product.id}"
        outcome = runner.execute(product_task_id, task, idempotency_key=key)
        report = outcome.report
        if not outcome.report.ok or outcome.report.output is None:
            problems_by_id.append(
                (
                    product.id,
                    (f"فشل التنفيذ في مرحلة «{outcome.report.stage}»: {outcome.report.detail_ar}",),
                )
            )
            continue
        try:
            parsed = parse_response(outcome.report.output, product)
        except ModelContractError as error:
            problems_by_id.append((product.id, (str(error),)))
            continue
        published.append(
            NasmaProduct(
                id=product.id,
                names=dict(parsed["name"]),
                categories=product.categories,
                price=product.price,
                slug=product.slug,
                image=product.image,
                image_alt=product.image_alt,
                tags=dict(parsed["tag"]),
                tone=product.tone,
            )
        )

    return CatalogRunResult(
        products=tuple(published),
        rejected=tuple(problems_by_id),
        outcome=outcome,
        report=report,
    )


def write_catalog(result: CatalogRunResult, path: str | Path) -> Path:
    """يكتب مخرجات الكتالوج بصيغة `/api/catalog` في نَسمة."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(result.as_dict(), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return file_path


def render_prompt_for(product: NasmaProduct) -> str:
    """واجهة صريحة لبناء الطلب (للاستخدام خارج المسار)."""
    return build_prompt(product)
