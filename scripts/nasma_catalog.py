#!/usr/bin/env python3
"""تشغيل مسار «نَسمة» الحيّ: ملف مورّد ⇒ كتالوج منتجات بثلاث لغات.

    python3 scripts/nasma_catalog.py --supplier tests/golden/supplier_rows.json
    python3 scripts/nasma_catalog.py --supplier data/supplier.csv --out artifacts/nasma

هذا **التطبيق الأول للشركة** (ADR 0002) من طرفه الأول: مستند IR ← حارس
الصلاحية ← حارس الميزانية ← التنفيذ المتين ← الموجّه ← النموذج الحقيقي ←
فحص العقد ← كتالوج جاهز لـ`/api/catalog` في نَسمة.

كل منتج مهمة مستقلة: فشل واحد لا يُسقط البقية، والاستئناف لا يُعيد ما نُفّذ.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from maestro.durable.journal import DurableJournal  # noqa: E402
from maestro.durable.runner import DurableRunner  # noqa: E402
from maestro.evidence.log import EvidenceLog  # noqa: E402
from maestro.guards.budget import BudgetGuard  # noqa: E402
from maestro.guards.permission import PermissionGuard  # noqa: E402
from maestro.integrations.nasma.catalog import load_supplier_rows  # noqa: E402
from maestro.integrations.nasma.pipeline import (  # noqa: E402
    default_registry,
    run_catalog,
    write_catalog,
)
from maestro.routing.base import RoutingPolicy  # noqa: E402
from maestro.routing.groq import groq_profile  # noqa: E402
from maestro.routing.http_provider import OpenAICompatibleProvider  # noqa: E402
from maestro.routing.openrouter import openrouter_deepseek_profile  # noqa: E402
from maestro.routing.router import ModelRouter  # noqa: E402
from maestro.runtime.runner import CapabilityRunner  # noqa: E402


def build_runner(out_dir: Path) -> DurableRunner:
    """يبني السلسلة الكاملة: حُرّاس ← موجّه ← تنفيذ متين."""
    registry = default_registry()
    router = ModelRouter(
        providers={
            "openrouter": OpenAICompatibleProvider(name="openrouter"),
            "groq": OpenAICompatibleProvider(name="groq"),
        },
        profiles={
            "openrouter": openrouter_deepseek_profile(),
            "groq": groq_profile(tier="fallback"),
        },
        policy=RoutingPolicy(tier_order=("api", "fallback")),
        budget=BudgetGuard(max_cost_usd=2.0, max_tokens=500_000),
    )
    permissions = PermissionGuard(
        allowed_capabilities=frozenset({"catalog.ingest"}),
        max_authority=2,
    )
    capability_runner = CapabilityRunner(
        registry, router, permissions, EvidenceLog(out_dir / "evidence.jsonl")
    )
    return DurableRunner(capability_runner, DurableJournal(out_dir / "journal.jsonl"))


def main() -> int:
    """يشغّل الكتالوج الحيّ ويطبع النتيجة."""
    parser = argparse.ArgumentParser(description="مسار نَسمة الحيّ — مورّد إلى كتالوج.")
    parser.add_argument("--supplier", required=True, help="ملف المورّد (JSON أو CSV)")
    parser.add_argument("--out", default="artifacts/nasma", help="مجلد المخرجات")
    parser.add_argument("--task-id", default="catalog", help="معرّف المهمة (للتكرارية)")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = load_supplier_rows(args.supplier)
    runner = build_runner(out_dir)
    result = run_catalog(rows, runner, task_id=args.task_id)

    catalog_path = write_catalog(result, out_dir / "catalog.json")
    report = {
        "published": [product.id for product in result.products],
        "rejected": [
            {"id": product_id, "reasons": list(reasons)}
            for product_id, reasons in result.rejected
        ],
        "status": result.outcome.status if result.outcome else None,
        "stage": result.report.stage if result.report else None,
        "cost_usd": round(sum(a.cost_usd for a in result.report.attempts), 8)
        if result.report
        else None,
        "tokens_in": sum(a.tokens_in for a in result.report.attempts) if result.report else None,
        "tokens_out": sum(a.tokens_out for a in result.report.attempts) if result.report else None,
        "attempts": [a.as_dict() for a in result.report.attempts] if result.report else [],
    }
    (out_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    for product in result.products:
        print(f"✔ {product.id} — {product.names.get('ar', '')} / {product.names.get('en', '')}")
    for product_id, reasons in result.rejected:
        print(f"✘ {product_id} — {'؛ '.join(reasons)}")

    print()
    print(f"منشور: {len(result.products)} · مرفوض: {len(result.rejected)}")
    print(f"التكلفة: {report['cost_usd']}$ · الكتالوج: {catalog_path}")

    if not result.products:
        print("لا منتج واحد نُشر — لا كتالوج ناقص يُكتب.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
