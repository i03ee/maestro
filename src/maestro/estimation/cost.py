"""تقدير تكلفة القدرة **قبل** التنفيذ.

لماذا؟ لأن «المجاني» في هذا المشروع تعني **صفر تكلفة إلزامية** — أي أن
التكلفة يجب أن تكون **معلومة قبل** الإنفاق لا بعده. التقدير هنا **أعلى
حدّ** (worst case): يجمع أسوأ سعر في السلسلة × أسوأ عدد رموز — فلا يفاجئنا
الفاتورة.

قاعدتان:
- **العدد لا النسبة**: نفس المدخلات ⇒ نفس الرقم بالضبط.
- **لا صفر صامت**: إذا لم يُسعَّر نموذجٌ في السلسلة، يُعلَن ذلك صراحةً ولا
  يُحسب صفراً. تقديرٌ ناقص يُرفض أن يمرّ كأنه مجاني.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..company.catalogue import Capability, capability_by_name
from ..routing.base import ModelProfile


@dataclass(frozen=True)
class CostEstimate:
    """تقدير تكلفة قدرة واحدة قبل تنفيذها."""

    capability: str
    ensemble: tuple[str, ...]
    max_cost_usd: float
    max_tokens: int
    per_model_cost_usd: tuple[tuple[str, float], ...]
    unpriced_models: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        """هل سُعّرت كل نماذج السلسلة؟"""
        return not self.unpriced_models

    def as_dict(self) -> dict[str, object]:
        return {
            "capability": self.capability,
            "ensemble": list(self.ensemble),
            "max_cost_usd": round(self.max_cost_usd, 6),
            "max_tokens": self.max_tokens,
            "per_model_cost_usd": [
                {"model": name, "cost_usd": round(cost, 6)}
                for name, cost in self.per_model_cost_usd
            ],
            "unpriced_models": list(self.unpriced_models),
            "complete": self.complete,
        }


def estimate_cost(
    *,
    capability_name: str,
    max_tokens: int,
    profiles_by_tier: dict[str, ModelProfile],
    ensemble: tuple[str, ...],
) -> CostEstimate:
    """يحسب أعلى تكلفة ممكنة عبر السلسلة.

    `profiles_by_tier` مفاتيحها **طبقات** السلسلة: `local` و`api` و`fallback`.
    النموذج غير المسعَّر يُذكر في `unpriced_models` ولا يُحسب صفراً.
    """
    per_model: list[tuple[str, float]] = []
    unpriced: list[str] = []
    for tier in ensemble:
        profile = profiles_by_tier.get(tier)
        if profile is None:
            unpriced.append(tier)
            continue
        per_model.append((tier, profile.estimate_cost(max_tokens, max_tokens)))
    return CostEstimate(
        capability=capability_name,
        ensemble=ensemble,
        max_cost_usd=sum(cost for _, cost in per_model),
        max_tokens=max_tokens,
        per_model_cost_usd=tuple(per_model),
        unpriced_models=tuple(unpriced),
    )


def worst_case_cost(
    capability: Capability,
    *,
    max_tokens: int,
    profiles_by_tier: dict[str, ModelProfile],
) -> CostEstimate:
    """تقدير قدرة من الكتالوج بأسوأ سعر في سلسلتها."""
    return estimate_cost(
        capability_name=capability.name,
        max_tokens=max_tokens,
        profiles_by_tier=profiles_by_tier,
        ensemble=capability.ensemble,
    )


def estimate_from_document(
    document: dict[str, object],
    *,
    profiles_by_tier: dict[str, ModelProfile],
) -> CostEstimate:
    """تقدير من مستند IR: يقرأ الميزانية والسلسلة منه."""
    capability_name = str(document.get("capability", ""))
    budget = document.get("budget") or {}
    max_tokens = int(budget.get("max_tokens", 0) or 0)
    redundancy = document.get("redundancy") or {}
    ensemble = tuple(str(item) for item in redundancy.get("ensemble", ()))
    if not ensemble:
        capability = capability_by_name(capability_name)
        if capability is not None:
            ensemble = capability.ensemble
    return estimate_cost(
        capability_name=capability_name,
        max_tokens=max_tokens,
        profiles_by_tier=profiles_by_tier,
        ensemble=ensemble,
    )
