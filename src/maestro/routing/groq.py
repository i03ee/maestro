"""بطاقات Groq — سرعة عالية بلا استنتاج، وسعر معلن من Groq نفسها.

الأرقام من صفحة نماذج Groq (`console.groq.com/docs/models`) بتاريخ 2026-11-18،
والسياق من واجهة `GET /openai/v1/models`:

| النموذج | سياق | إخراج $/مليون | إدخال $/مليون | الحالة |
|---|---:|---:|---:|---|
| `openai/gpt-oss-120b` | 131,072 | 0.60 | 0.15 | إنتاج |
| `openai/gpt-oss-20b` | 131,072 | 0.30 | 0.075 | إنتاج |
| `qwen/qwen3.8-27b` | 131,072 | 4.00 | 0.80 | معاينة |

**القياس الحيّ (2026-11-18)**: `qwen/qwen3.8-27b` حرّر بطاقة منتج بثلاث لغات
في 1.5 ثانية (282 رمزاً) — وهو المسار الأسرع المتاح، لكنه **أغلى** من
DeepSeek عبر OpenRouter بأكثر من عشرة أضعاف في الإدخال.

الترتيب Economي المقترح للسلسلة: محلي (مجاني) ← OpenRouter/DeepSeek
(الأرخص) ← Groq `gpt-oss-20b` (احتياطي سريع). أما `qwen/qwen3.8-27b` فهو
مخصّص للّياقة اللغوية (العربية والكردية) لا للسلسلة الاقتصادية.
"""

from __future__ import annotations

from .base import ModelProfile

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_API_KEY_ENV = "GROQ_API_KEY"

#: (سعر الإدخال، سعر الإخراج، السياق) لكل نموذج — كما تعلنه Groq.
GROQ_MODEL_PRICES: dict[str, tuple[float, float, int]] = {
    "openai/gpt-oss-120b": (0.15, 0.60, 131_072),
    "openai/gpt-oss-20b": (0.075, 0.30, 131_072),
    "qwen/qwen3.8-27b": (0.80, 4.00, 131_072),
}

#: النموذج الافتراضي: الأرخص إنتاجاً على Groq.
GROQ_DEFAULT_MODEL = "openai/gpt-oss-20b"


def groq_profile(
    name: str = "groq",
    *,
    model: str = GROQ_DEFAULT_MODEL,
    tier: str = "api",
    base_url: str = GROQ_BASE_URL,
) -> ModelProfile:
    """بطاقة نموذج على Groq.

    نموذج غير معروف ⇒ `ValueError` بExplicit: بطاقة بلا سعر تُفسد تقدير
    التكلفة، والتقدير بلا سعر لا يجوز أن يُخمَّن بصمت.
    """
    try:
        cost_in, cost_out, context = GROQ_MODEL_PRICES[model]
    except KeyError as error:
        known = "، ".join(sorted(GROQ_MODEL_PRICES))
        raise ValueError(
            f"نموذج Groq غير معروف: {model}. المعروف: {known}. "
            "أضف سعره إلى GROQ_MODEL_PRICES أولاً."
        ) from error
    return ModelProfile(
        name=name,
        tier=tier,
        model=model,
        cost_in_per_mtok=cost_in,
        cost_out_per_mtok=cost_out,
        max_context=context,
        supports_tools=True,
        supports_vision=False,
        api_key_env=GROQ_API_KEY_ENV,
        base_url=base_url,
    )


def groq_fast_profile(name: str = "groq-fast") -> ModelProfile:
    """أسرع بطاقة على Groq: `gpt-oss-20b`."""
    return groq_profile(name, model="openai/gpt-oss-20b")


def groq_quality_profile(name: str = "groq-quality") -> ModelProfile:
    """أقوى بطاقة على Groq: `gpt-oss-120b`."""
    return groq_profile(name, model="openai/gpt-oss-120b")


def groq_arabic_profile(name: str = "groq-arabic") -> ModelProfile:
    """بطاقة المعاينة العربية: `qwen/qwen3.8-27b` (أغلى، وأسرع)."""
    return groq_profile(name, model="qwen/qwen3.8-27b")
