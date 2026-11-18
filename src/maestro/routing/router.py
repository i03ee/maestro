"""الموجّه: يختار النموذج، يراقب الميزانية، ويُسقط منظّماً عند الفشل."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from ..evidence.log import EvidenceLog
from ..guards.budget import BudgetExceeded, BudgetGuard
from .base import (
    CompletionRequest,
    CompletionResponse,
    ModelProfile,
    Provider,
    RoutingPolicy,
)


@dataclass(frozen=True)
class Attempt:
    """محاولة واحدة على نموذج واحد."""

    provider: str
    model: str
    status: str
    detail: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "detail": self.detail,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": self.cost_usd,
        }


@dataclass(frozen=True)
class RouterResult:
    """نتيجة موجّهة ناجحة."""

    text: str
    provider: str
    model: str
    attempts: tuple[Attempt, ...]
    cost_usd: float
    tokens_in: int
    tokens_out: int

    @property
    def fallback_used(self) -> bool:
        """هل احتاج الأمر إلى إسقاط فعلي؟"""
        return any(attempt.status in {"failed", "empty_output"} for attempt in self.attempts)


class RoutingFailure(RuntimeError):
    """كل النماذج في السلسلة فشلت."""

    def __init__(self, attempts: tuple[Attempt, ...]):
        self.attempts = attempts
        summary = "; ".join(f"{a.provider}:{a.status}" for a in attempts) or "لا محاولات"
        super().__init__(f"فشل التنفيذ على كل النماذج — {summary}")


@dataclass
class ModelRouter:
    """موجّه نماذج بثلاث طبقات: محلي، ثم واجهة، ثم احتياطي."""

    providers: dict[str, Provider]
    profiles: dict[str, ModelProfile]
    policy: RoutingPolicy = field(default_factory=RoutingPolicy)
    budget: BudgetGuard = field(default_factory=lambda: BudgetGuard())
    evidence: EvidenceLog | None = None

    def run(self, request: CompletionRequest) -> RouterResult:
        """ينفّذ الطلب على السلسلة المرتّبة، ويتوقف عند أول نجاح."""
        chain = self.policy.chain_for(request.capability, self.profiles)
        if not chain:
            raise RoutingFailure(())

        attempts: list[Attempt] = []
        for name in chain:
            profile = self.profiles[name]
            provider = self.providers.get(name)
            if provider is None:
                attempts.append(Attempt(name, profile.model, "skipped_no_provider"))
                continue
            if profile.api_key_env and not os.environ.get(profile.api_key_env):
                attempts.append(
                    Attempt(
                        name,
                        profile.model,
                        "skipped_missing_credentials",
                        f"المتغيّر {profile.api_key_env} غير مضبوط",
                    )
                )
                continue
            if request.tools and not profile.supports_tools:
                attempts.append(
                    Attempt(name, profile.model, "skipped_tool_unsupported", "النموذج بلا أدوات")
                )
                continue

            estimate = profile.estimate_cost(
                max(1, len(request.prompt) // 4), request.max_output_tokens
            )
            self.budget.authorize(estimate, request.max_output_tokens)

            try:
                response: CompletionResponse = provider.complete(request, profile)
            except Exception as error:  # noqa: BLE001 — يُسجَّل ثم يُسقَط
                attempts.append(
                    Attempt(name, profile.model, "failed", f"{type(error).__name__}: {error}")
                )
                continue

            if not response.text.strip():
                attempts.append(Attempt(name, profile.model, "empty_output"))
                continue

            cost = profile.estimate_cost(response.tokens_in, response.tokens_out)
            self.budget.consume(cost, response.tokens_in + response.tokens_out)
            attempts.append(
                Attempt(
                    name,
                    response.model or profile.model,
                    "ok",
                    tokens_in=response.tokens_in,
                    tokens_out=response.tokens_out,
                    cost_usd=cost,
                )
            )
            result = RouterResult(
                text=response.text,
                provider=name,
                model=response.model or profile.model,
                attempts=tuple(attempts),
                cost_usd=cost,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
            )
            if self.evidence is not None:
                self.evidence.append(
                    "routing",
                    {
                        "capability": request.capability,
                        "provider": result.provider,
                        "model": result.model,
                        "attempts": [a.as_dict() for a in result.attempts],
                        "cost_usd": result.cost_usd,
                        "tokens_in": result.tokens_in,
                        "tokens_out": result.tokens_out,
                    },
                )
            return result

        raise RoutingFailure(tuple(attempts))
