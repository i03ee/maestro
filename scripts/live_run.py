#!/usr/bin/env python3
"""المسار الحيّ: ينتج artefactات حقيقية من نموذج حقيقي، ويسجّل التكلفة.

    python3 scripts/live_run.py --idea "منصة تجارة جمال عراقية بثلاث لغات"
    python3 scripts/live_run.py --capability idea.prd --idea "..."
    python3 scripts/live_run.py --provider groq --out artifacts/

السلسلة المستعملة بالترتيب: **محلي** (إن توفّر) ← **OpenRouter/DeepSeek** ←
**Groq**. ولو لم يتوفّر مفتاح، تُتخطّى الطبقة ويُعلَن ما تبقّى. **بلا مفتاح
ولا مسار محلي ⇒ الفشل يُبلَّغ ولا artefact يُكتب.**

المخرجات:
- `artifacts/prd.md` و`artifacts/user_stories.json` (قدرة idea.prd)
- `artifacts/market/competitor_matrix.csv` (research.competitors)
- `artifacts/research/candidates.jsonl` + `scans/` + `decisions/` (research.candidates)
- `artifacts/live_run.json`: تقرير الجولة (المزوّد، النموذج، التكلفة، الزمن)

رمز الخروج: 0 إذا نجحت كل القدرات المطلوبة، 1 إذا فشل واحدة.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from maestro.evidence.log import EvidenceLog  # noqa: E402
from maestro.producers.live import run_live  # noqa: E402
from maestro.routing.base import RoutingPolicy  # noqa: E402
from maestro.routing.groq import groq_profile  # noqa: E402
from maestro.routing.http_provider import OpenAICompatibleProvider  # noqa: E402
from maestro.routing.local import ollama_profile  # noqa: E402
from maestro.routing.openrouter import openrouter_deepseek_profile  # noqa: E402
from maestro.routing.router import ModelRouter  # noqa: E402

CAPABILITIES: tuple[str, ...] = ("idea.prd", "research.competitors", "research.candidates")

DEFAULT_IDEA = (
    "منصة تجارة إلكترونية للتجارة العراقية (نَسمة): منتجات العناية والجمال، "
    "واجهة عربية/كردية/إنجليزية، أسعار بالدينار العراقي، ودفع عند الاستلام. "
    "الجمهور: نساء عراقيات يبحثن عن منتجات موثوقة بأسعار واضحة."
)
DEFAULT_MARKET = (
    "متاجر الجمال IraqBeauty و Namshi و AsaibBeauty — سوق تجارة الجمال "
    "IRAكي بالتجارة الإلكترونية مع دعم العربية والكردية."
)
DEFAULT_NEED = (
    "مكوّنات مفتوحة المصدر لبناء: فهرسة منتجات، بحث بالعرربية والكردية، "
    "بوابة دفع، ونشر تطبيق أندرويد."
)


def build_router(out_dir: Path) -> ModelRouter:
    """يبني الموجّه بالسلسلة: محلي ← OpenRouter ← Groq."""
    providers = {
        "local": OpenAICompatibleProvider(name="local"),
        "openrouter": OpenAICompatibleProvider(name="openrouter"),
        "groq": OpenAICompatibleProvider(name="groq"),
    }
    profiles = {
        "local": ollama_profile(),
        "openrouter": openrouter_deepseek_profile(),
        # Groq طبقة «fallback»: أرخصُ ما هو OpenRouter (0.036$ مقابل 0.075$)
        # فالترتيب هنا هو الترتيب الاقتصادي لا الأبجدي.
        "groq": groq_profile(tier="fallback"),
    }
    evidence = EvidenceLog(out_dir / "artifacts" / "evidence.jsonl")
    return ModelRouter(
        providers=providers,
        profiles=profiles,
        policy=RoutingPolicy(tier_order=("local", "api", "fallback")),
        evidence=evidence,
    )


def check_urls(matrix_path: Path, timeout: int = 10) -> list[dict[str, object]]:
    """يفحص روابط جدول المنافسين ويسجّل ما استجاب.

    لماذا؟ لأن ردّ النموذج **فرضية**: قد يخترع نطاقاً. الفحص هنا لا يثبت
    صحّة المحتوى، ولا ينفي وجود الموقع (حجبٌ جغرافي أو 403 لا يعني
    nonexistence) — لكنه يكشف الروابط التي لا تستجيب أصلاً.
    """
    checks: list[dict[str, object]] = []
    if not matrix_path.is_file():
        return checks
    rows = list(csv.DictReader(matrix_path.read_text(encoding="utf-8").splitlines()))
    for row in rows:
        url = (row.get("url") or "").strip()
        if not url:
            continue
        if not url.startswith(("http://", "https://")):
            # النموذج كتب «غير معروف» حقلاً — هذا ليس رابطاً، بل نقصٌ صريح.
            checks.append({"url": url, "status": None, "responded": False, "detail": "not_a_url"})
            continue
        request = urllib.request.Request(
            url, method="GET", headers={"User-Agent": "Mozilla/5.0 (compatible; maestro-check)"}
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                checks.append({"url": url, "status": response.status, "responded": True})
        except urllib.error.HTTPError as error:
            # ردّ HTTP هو ردّ: الموقع موجود لكنّه رفض الطلب (403 حجبٌ مثلاً).
            checks.append({"url": url, "status": error.code, "responded": True})
        except Exception as error:  # noqa: BLE001 — الفحص لا يُسقط الجولة
            checks.append(
                {"url": url, "status": None, "responded": False, "detail": type(error).__name__}
            )
    return checks


def payloads(idea: str, market: str, need: str) -> dict[str, dict[str, str]]:
    """مدخلات كل قدرة."""
    return {
        "idea.prd": {"idea": idea},
        "research.competitors": {"market": market},
        "research.candidates": {"need": need},
    }


def main() -> int:
    """يشغّل القدرات المطلوبة ويطبع التقرير."""
    parser = argparse.ArgumentParser(description="المسار الحيّ — إنتاج artefactات حقيقية.")
    parser.add_argument("--idea", default=DEFAULT_IDEA, help="الفكرة (قدرة idea.prd)")
    parser.add_argument("--market", default=DEFAULT_MARKET, help="السوق (research.competitors)")
    parser.add_argument("--need", default=DEFAULT_NEED, help="الحاجة (research.candidates)")
    parser.add_argument(
        "--capability",
        action="append",
        choices=CAPABILITIES,
        help="قدرة واحدة ( repeatable ). الافتراضي: الثلاث.",
    )
    parser.add_argument(
        "--out", default=".", help="جذر المشروع (تُكتب المخرجات في <out>/artifacts/)"
    )
    parser.add_argument("--report", default=None, help="مسار تقرير الجولة (JSON)")
    args = parser.parse_args()

    capabilities = tuple(args.capability) if args.capability else CAPABILITIES
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    router = build_router(out_dir)
    data = payloads(args.idea, args.market, args.need)

    outcomes = []
    failures = []
    url_checks: list[dict[str, object]] = []
    for capability in capabilities:
        try:
            outcome = run_live(router, capability, data[capability], out_dir)
        except Exception as error:  # noqa: BLE001 — يُبلَّغ الفشل كما هو
            failures.append({"capability": capability, "error": f"{type(error).__name__}: {error}"})
            print(f"✘ {capability}: {type(error).__name__}: {error}")
            continue
        if capability == "research.competitors":
            matrix = out_dir / "artifacts" / "market" / "competitor_matrix.csv"
            url_checks = check_urls(matrix)
            checks_path = out_dir / "artifacts" / "market" / "url_checks.json"
            checks_path.parent.mkdir(parents=True, exist_ok=True)
            checks_path.write_text(
                json.dumps(url_checks, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            responded = sum(1 for item in url_checks if item["responded"])
            print(f"    فحص الروابط: {responded}/{len(url_checks)} استجاب ⇒ {checks_path}")
        outcomes.append(outcome.as_dict())
        print(
            f"✔ {capability:24s} {outcome.provider}/{outcome.model} "
            f"${outcome.cost_usd:.6f} {outcome.elapsed_ms}ms"
        )
        for artefact in outcome.artefacts:
            print(f"    → {artefact}")

    report = {
        "kind": "live-run",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "capabilities": list(capabilities),
        "outcomes": outcomes,
        "failures": failures,
        "total_cost_usd": round(sum(item["cost_usd"] for item in outcomes), 8),
        "url_checks": url_checks,
        "url_checks_responded": sum(1 for item in url_checks if item["responded"]),
    }
    report_path = Path(args.report) if args.report else out_dir / "artifacts" / "live_run.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"التكلفة الكلية: ${report['total_cost_usd']:.6f}")
    print(f"التقرير: {report_path}")

    if failures:
        print(f"فشل {len(failures)} قدرة — لا artefact ناقص يُكتب.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
