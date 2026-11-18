"""مُشغّل مجموعات التقييم: كل حالة تجتاز أو تفشل."""

from __future__ import annotations

from dataclasses import dataclass

from ..guards.budget import BudgetGuard
from ..guards.permission import PermissionGuard
from ..routing.base import CompletionResponse, ModelProfile
from ..routing.offline import ScriptedProvider
from ..routing.router import ModelRouter
from ..runtime.registry import CapabilityRegistry
from ..runtime.runner import CapabilityRunner
from .cases import CASES, EvalCase


@dataclass(frozen=True)
class EvalOutcome:
    """نتيجة حالة تقييم."""

    case_id: str
    ok: bool
    problems: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"case_id": self.case_id, "ok": self.ok, "problems": list(self.problems)}


def eval_registry() -> CapabilityRegistry:
    """سجل قدرات يغطّي حالات التقييم.

    كتالوج الشركة فيه 24 قدرة، و«media.render» ليست منها: هي قدرة
    توضيحية للاختبار. تُسجَّل هنا صراحةً بدل أن تُضاف إلى الكتالوج.
    """
    from ..company.registry import build_registry
    from ..runtime.spec import CapabilitySpec

    registry = build_registry()
    registry.register(
        CapabilitySpec(
            name="media.render",
            description_ar="توليد صورة (قدرة توضيحية للاختبار)",
            required_tools=("render.image",),
            default_authority=1,
        )
    )
    return registry


def evaluate_case(case: EvalCase) -> EvalOutcome:
    """ينفّذ حالة واحدة عبر المسار الكامل ويفحص مخرجها."""
    profile = ModelProfile(
        name="stub",
        tier="local",
        model="eval-stub",
        cost_in_per_mtok=0.0,
        cost_out_per_mtok=0.0,
        max_context=32768,
    )
    provider = ScriptedProvider(
        "stub", [CompletionResponse(text=case.reply, tokens_in=10, tokens_out=20, model="eval-stub")]
    )
    router = ModelRouter(
        providers={"stub": provider},
        profiles={"stub": profile},
        budget=BudgetGuard(max_cost_usd=5.0, max_tokens=500_000),
    )
    runner = CapabilityRunner(
        eval_registry(),
        router,
        PermissionGuard(
            allowed_capabilities=frozenset({case.capability}), max_authority=3
        ),
    )
    report = runner.run(case.document)
    if not report.ok:
        return EvalOutcome(
            case_id=case.id,
            ok=False,
            problems=(f"التنفيذ رُفض في مرحلة «{report.stage}»: {report.detail_ar}",),
        )
    problems = tuple(case.check(report.output or ""))
    return EvalOutcome(case_id=case.id, ok=not problems, problems=problems)


def run_all_cases() -> list[EvalOutcome]:
    """يشغّل كل الحالات."""
    return [evaluate_case(case) for case in CASES]
