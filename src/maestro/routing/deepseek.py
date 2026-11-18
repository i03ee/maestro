"""بطاقات نماذج DeepSeek — الموجّه يتكلم معها كما يتكلم مع غيرها.

الأسعار المسجّلة هي أسعار نهاية 2026/11 كما وردت في بحثstack المفتوح:
سعر منخفض في أوقات الهدوء (01:00–04:00 و06:00–10:00 UTC في أيام العمل)
وأعلى في الذروة. النموذج `deepseek-flash` = V4.1-Flash-1017 بسياق 1M ورمز
إخراج 384K، ويدعم الأدوات والرؤية وJSON.
"""

from __future__ import annotations

from .base import ModelProfile

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"


def deepseek_flash_profile(
    name: str = "deepseek",
    *,
    off_peak: bool = True,
    base_url: str = DEEPSEEK_BASE_URL,
) -> ModelProfile:
    """بطاقة نموذج DeepSeek Flash بسعر يناسب الوقت."""
    cost_in = 0.15 if off_peak else 0.30
    cost_out = 0.60 if off_peak else 1.20
    return ModelProfile(
        name=name,
        tier="api",
        model="deepseek-flash",
        cost_in_per_mtok=cost_in,
        cost_out_per_mtok=cost_out,
        max_context=1_000_000,
        supports_tools=True,
        supports_vision=True,
        api_key_env=DEEPSEEK_API_KEY_ENV,
        base_url=base_url,
    )


def deepseek_fallback_profile(
    name: str = "deepseek-fallback", *, base_url: str = DEEPSEEK_BASE_URL
) -> ModelProfile:
    """نموذج احتياطي من نفس المزوّد (تبديل نموذج لا مزوّد)."""
    return ModelProfile(
        name=name,
        tier="fallback",
        model="deepseek-chat",
        cost_in_per_mtok=0.30,
        cost_out_per_mtok=1.20,
        max_context=128_000,
        supports_tools=True,
        supports_vision=False,
        api_key_env=DEEPSEEK_API_KEY_ENV,
        base_url=base_url,
    )
