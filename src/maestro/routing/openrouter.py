"""بطاقات OpenRouter — DeepSeek V4.1-Flash-1017 بسعر *أقلّ* من الطلب المباشر.

كل الأرقام هنا مقروءة من واجهة OpenRouter نفسها (`GET /api/v1/models`) بتاريخ
2026-11-18، لا من تخمين:

| النموذج | سياق | إدخال $/مليون | إخراج $/مليون | قراءة الكاش $/مليون |
|---|---:|---:|---:|---:|
| `deepseek/deepseek-v4.1-flash-1017` | 1,048,576 | 0.036 | 0.50 | 0.01 |

مقارنةً بسعر DeepSeek المباشر (0.15/0.60 في الهدوء و0.30/1.20 في الذروة):
**الطريق عبر OpenRouter أرخص من الطلب المباشر في كل الأوقات** لهذا النموذج،
ويصلح الغرضين معاً: النموذج نفسه، وسعر ثابت لا يتضاعف مع ساعة الذروة.

## النموذج نموذج تفكير — وهذا ما يجب ضبطه

`deepseek-v4.1-flash-1017` **نموذج تفكير**: يستهلك رموزاً في `reasoning` قبل
الإجابة. القياس الحيّ (2026-11-18):

- بلا ضبط: استهلك 800/800 رمزاً في التفكير وأعاد `content` فارغاً ⇒ لا إجابة.
- مع `reasoning.effort = low`: أنتج 448 حرفاً JSON صالحاً، ورموز التفكير 728،
  والتكلفة 0.00028$.

لذلك تحمل البطاقة `reasoning` مدمجاً. من يتجاوزها بحجة «سأرفع سقف الرموز»
يدفع أكثر ويخسر أكثر.
"""

from __future__ import annotations

from .base import ModelProfile, with_extra_body

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"

#: سعر DeepSeek V4.1-Flash-1017 عبر OpenRouter لكل مليون رمز (2026-11-18).
DEEPSEEK_V41_FLASH_IN_PER_MTOK = 0.036
DEEPSEEK_V41_FLASH_OUT_PER_MTOK = 0.50
#: سياق النموذج كما يعلنه OpenRouter: 1M رمز.
DEEPSEEK_V41_FLASH_CONTEXT = 1_048_576
#: النموذج الافتراضي على OpenRouter.
DEEPSEEK_V41_FLASH_MODEL = "deepseek/deepseek-v4.1-flash-1017"


def openrouter_deepseek_profile(
    name: str = "openrouter-deepseek",
    *,
    model: str = DEEPSEEK_V41_FLASH_MODEL,
    reasoning_effort: str = "low",
    base_url: str = OPENROUTER_BASE_URL,
) -> ModelProfile:
    """بطاقة DeepSeek عبر OpenRouter مع ضبط الجهد إلى «low» افتراضياً.

    `reasoning_effort=None` تعني: لا تُرسل حقل `reasoning` إطلاقاً — حينها
    يستهلك النموذج كل سقف الرموز في التفكير ما لم يرفع المستخدم السقف.
    """
    profile = ModelProfile(
        name=name,
        tier="api",
        model=model,
        cost_in_per_mtok=DEEPSEEK_V41_FLASH_IN_PER_MTOK,
        cost_out_per_mtok=DEEPSEEK_V41_FLASH_OUT_PER_MTOK,
        max_context=DEEPSEEK_V41_FLASH_CONTEXT,
        supports_tools=True,
        supports_vision=True,
        api_key_env=OPENROUTER_API_KEY_ENV,
        base_url=base_url,
    )
    if reasoning_effort is None:
        return profile
    return with_extra_body(profile, {"reasoning": {"effort": reasoning_effort}})
