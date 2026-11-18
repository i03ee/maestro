"""بطاقة النموذج المحلي.

النموذج المحلي (Qwen وأمثاله) يعمل على جهازك: **تكلفة صفر، لا مفتاح، لا
شبكة**. ولهذا هو الطبقة الأولى في كل سلسلة — قبل أن يُلمس شيءٌ مدفوع.
"""

from __future__ import annotations

from .base import ModelProfile

#: عنوان خادم محلي متوافق مع OpenAI (Ollama افتراضياً).
DEFAULT_LOCAL_BASE_URL = "http://127.0.0.1:11434/v1"


def local_profile(name: str = "local", model: str = "qwen-local") -> ModelProfile:
    """بطاقة نموذج محلي بتكلفة صفر."""
    return ModelProfile(
        name=name,
        tier="local",
        model=model,
        cost_in_per_mtok=0.0,
        cost_out_per_mtok=0.0,
        max_context=32_768,
        supports_tools=True,
        supports_vision=False,
        api_key_env=None,
        base_url="http://127.0.0.1:11434/v1",
    )


def ollama_profile(
    name: str = "local",
    *,
    model: str = "qwen2.5-coder:7b",
    base_url: str = DEFAULT_LOCAL_BASE_URL,
) -> ModelProfile:
    """بطاقة نموذج محلي على خادم متوافق مع OpenAI (بلا مفتاح، بلا تكلفة).

    هذه هي الطبقة الأولى في كل سلسلة: **صفر تكلفة، وبيانات لا تغادر
    جهازك**. والسقف: جودة النماذج المحلية على المهام الصعبة أقل من
    النماذج السحابية — ولذلك القدرات الحرجة تُنفَّذ بنموذجين على الأقل.
    """
    return ModelProfile(
        name=name,
        tier="local",
        model=model,
        cost_in_per_mtok=0.0,
        cost_out_per_mtok=0.0,
        max_context=32_768,
        supports_tools=True,
        supports_vision=False,
        api_key_env=None,
        base_url=base_url,
    )
