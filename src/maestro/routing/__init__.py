"""توجيه النماذج: سلسلة نماذج واحدة، وإسقاط منظّم."""

from .base import (
    CompletionRequest,
    CompletionResponse,
    ModelProfile,
    Provider,
    RoutingPolicy,
    with_extra_body,
)
from .deepseek import deepseek_fallback_profile, deepseek_flash_profile
from .groq import (
    groq_arabic_profile,
    groq_fast_profile,
    groq_profile,
    groq_quality_profile,
)
from .openrouter import openrouter_deepseek_profile
from .offline import ScriptedProvider
from .router import Attempt, RouterResult, RoutingFailure, ModelRouter

__all__ = [
    "CompletionRequest",
    "deepseek_fallback_profile",
    "deepseek_flash_profile",
    "groq_arabic_profile",
    "groq_fast_profile",
    "groq_profile",
    "groq_quality_profile",
    "openrouter_deepseek_profile",
    "with_extra_body",
    "CompletionResponse",
    "ModelProfile",
    "Provider",
    "RoutingPolicy",
    "ScriptedProvider",
    "Attempt",
    "RouterResult",
    "RoutingFailure",
    "ModelRouter",
]
