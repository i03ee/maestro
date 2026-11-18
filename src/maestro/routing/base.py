"""أنواع أساسية للتوجيه: بطاقة النموذج، الطلب، والاستراتيجية."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Protocol, Sequence


@dataclass(frozen=True)
class ModelProfile:
    """بطاقة نموذج: أين يعمل، وكم يكلّف، وما يستطيع."""

    name: str
    tier: str
    model: str
    cost_in_per_mtok: float
    cost_out_per_mtok: float
    max_context: int
    supports_tools: bool = True
    supports_vision: bool = False
    api_key_env: str | None = None
    base_url: str | None = None
    #: جسم إضافي بصيغة JSON يُدمج في طلب المزوّد (مثل `reasoning`).
    extra_body: str = ""

    def estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        """تكلفة الطلب بالدولار، محسوبة من سعر المليون رمز."""
        return (
            tokens_in / 1_000_000 * self.cost_in_per_mtok
            + tokens_out / 1_000_000 * self.cost_out_per_mtok
        )


def with_extra_body(profile: ModelProfile, body: dict) -> ModelProfile:
    """نسخة من بطاقة النموذج بعد إضافة جسم JSON إلى الطلب.

    يُخزَّن JSON كنصّ ليبقى الملف قابلاً للتسلسل والمقارنة بلا مسائل hash.
    """
    return replace(profile, extra_body=json.dumps(body, ensure_ascii=False, sort_keys=True))


@dataclass(frozen=True)
class CompletionRequest:
    """طلب إكمال واحد، مستقل عن المزوّد."""

    capability: str
    prompt: str
    max_output_tokens: int = 1024
    tools: tuple[str, ...] = ()
    authority: int = 1


@dataclass(frozen=True)
class CompletionResponse:
    """ردّ المزوّد بعد التطبيع."""

    text: str
    tokens_in: int
    tokens_out: int
    model: str


class Provider(Protocol):
    """أي مزوّد يستوفي هذه الواجهة يعمل مع الموجّه بلا تعديل."""

    name: str

    def complete(self, request: CompletionRequest, profile: ModelProfile) -> CompletionResponse:
        ...


@dataclass(frozen=True)
class RoutingPolicy:
    """ترتيب الإسقاط بين الطبقات، مع تجاوزات لكل قدرة.

    الترتيب ثابت ولا عشوائي: النتيجة نفسها تُنتَج في كل تشغيل.
    """

    tier_order: tuple[str, ...] = ("local", "api", "fallback")
    capability_overrides: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def chain_for(self, capability: str, profiles: dict[str, ModelProfile]) -> tuple[str, ...]:
        """سلسلة أسماء النماذج لقدرة معيّنة، بالترتيب."""
        override = self.capability_overrides.get(capability)
        if override:
            return tuple(name for name in override if name in profiles)
        ordered = [
            name
            for name, profile in profiles.items()
            if profile.tier in self.tier_order
        ]
        ordered.sort(key=lambda name: (self.tier_order.index(profiles[name].tier), name))
        return tuple(ordered)
