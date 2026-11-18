"""بطاقة النموذج المحلي.

النموذج المحلي (Qwen وأمثاله) يعمل على جهازك: **تكلفة صفر، لا مفتاح، لا
شبكة**. ولهذا هو الطبقة الأولى في كل سلسلة — قبل أن يُلمس شيءٌ مدفوع.
"""

from __future__ import annotations

from .base import ModelProfile


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
