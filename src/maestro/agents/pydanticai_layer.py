"""مزوّد PydanticAI خلف واجهة `Provider` الموحّدة.

هذا هو الحدّ الفاصل الحقيقي: النواة لا تعرف PydanticAI ولا تفترضه، والمتّفق
عليه واجهة `Provider` واحدة. لذلك يعمل الموجّه مع مزوّد محلي، ومزوّد HTTP
مباشر، ومزوّد PydanticAI — بالاختبارات نفسها.

ملاحظة على الأرقام: التوقيع أُعيد بناؤه على شيفرة **PydanticAI 2.70**
(أصدَر 2026-11-17) لا على ما ورد في المقترح: الصنف اسمه `FallbackModel`
(في `pydantic_ai.models.fallback`) لا `ModelFallback`، وDeepSeek له مزوّد
أصلي `DeepSeekProvider` يقرأ `DEEPSEEK_API_KEY` من البيئة.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from ..routing.base import CompletionRequest, CompletionResponse, ModelProfile
from ._sync import AgentLayerError, run_sync

try:  # pragma: no cover — الاعتماد اختياري
    from pydantic_ai import Agent
    from pydantic_ai.exceptions import ModelAPIError, UsageLimitExceeded, UserError
    from pydantic_ai.models.fallback import FallbackModel
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.deepseek import DeepSeekProvider
    from pydantic_ai.usage import UsageLimits

    PYDANTIC_AI_AVAILABLE = True
except ImportError:  # pragma: no cover
    Agent = None  # type: ignore[assignment]
    FallbackModel = None  # type: ignore[assignment]
    OpenAIChatModel = None  # type: ignore[assignment]
    DeepSeekProvider = None  # type: ignore[assignment]
    UsageLimits = None  # type: ignore[assignment]
    ModelAPIError = RuntimeError  # type: ignore[assignment]
    UsageLimitExceeded = RuntimeError  # type: ignore[assignment]
    UserError = RuntimeError  # type: ignore[assignment]
    PYDANTIC_AI_AVAILABLE = False

DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"


@dataclass
class PydanticAIProvider:
    """مزوّد يغلّف وكيل PydanticAI خلف واجهة `Provider`."""

    name: str
    agent: Any
    request_timeout: float = 120.0
    max_requests: int = 3

    def complete(self, request: CompletionRequest, profile: ModelProfile) -> CompletionResponse:
        """ينفّذ الطلب عبر الوكيل ويعيد ردّاً معدَّلاً."""
        if not PYDANTIC_AI_AVAILABLE:
            raise AgentLayerError(
                "طبقة الوكلاء غير مثبّتة. ثبّت المجموعة الاختيارية: pip install -e '.[agent]'"
            )
        result = run_sync(lambda: self._run(request))
        usage = result.usage
        if callable(usage):  # PydanticAI 2.70 جعلها خاصية؛ ما قبلها دالة
            usage = usage()
        return CompletionResponse(
            text=str(result.output),
            tokens_in=int(getattr(usage, "input_tokens", 0) or 0),
            tokens_out=int(getattr(usage, "output_tokens", 0) or 0),
            model=profile.model,
        )

    async def _run(self, request: CompletionRequest) -> Any:
        """التشغيل الفعلي مع حدود استعمال صريحة."""
        limits = UsageLimits(
            request_limit=self.max_requests,
            output_tokens_limit=request.max_output_tokens,
        )
        return await self.agent.run(
            request.prompt,
            usage_limits=limits,
            timeout=self.request_timeout,
        )


def build_deepseek_agent(
    *,
    model_name: str = "deepseek-flash",
    api_key: str | None = None,
    base_url: str | None = None,
    instructions: str | None = None,
    output_type: Any = str,
    retries: int = 2,
    fallback_model_name: str | None = None,
) -> Any:
    """يبني وكيلاً على DeepSeek، مع نموذج احتياطي اختياري.

    لا يُبنى الوكيل بلا مفتاح: البناء بلا مفتاح يفشل مبكراً، لا عند أول طلب.
    """
    if not PYDANTIC_AI_AVAILABLE:
        raise AgentLayerError(
            "طبقة الوكلاء غير مثبّتة. ثبّت المجموعة الاختيارية: pip install -e '.[agent]'"
        )
    key = api_key or os.environ.get(DEEPSEEK_API_KEY_ENV)
    if not key:
        raise AgentLayerError(
            f"المتغيّر {DEEPSEEK_API_KEY_ENV} غير مضبوط؛ لا يُبنى وكيل بلا مفتاح."
        )
    provider = DeepSeekProvider(api_key=key, base_url=base_url)
    model = OpenAIChatModel(model_name, provider=provider)
    if fallback_model_name:
        fallback_provider = DeepSeekProvider(api_key=key, base_url=base_url)
        model = FallbackModel(
            model,
            OpenAIChatModel(fallback_model_name, provider=fallback_provider),
        )
    return Agent(
        model=model,
        instructions=instructions,
        output_type=output_type,
        retries=retries,
    )
