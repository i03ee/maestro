"""عقد الطلب والاستجابة مع النموذج في قدرة «بيانات المنتج».

العقد صارم: يطلب النموذج JSON محدَّد الحقول، ويرفض أي ردّ آخر. لا يُقبل
ردّ جزئي ولا نص حرّ — الفشل يُبلَّغ، ولا يُملأ الفراغ بالتخمين.
"""

from __future__ import annotations

import json
from typing import Any

from .catalog import LOCALES, NasmaProduct

#: حقل الردّ المطلوب من النموذج لكل منتج.
RESPONSE_FIELDS: tuple[str, ...] = ("id", "name", "tag", "description")


def build_prompt(product: NasmaProduct) -> str:
    """يبني نص الطلب: حقول المنتج بالعربية + عقد الردّ."""
    payload = {
        "product_id": product.id,
        "source_name_ar": product.names.get("ar", ""),
        "source_name_en": product.names.get("en", ""),
        "category_ar": product.categories.get("ar", ""),
        "price_iqd": product.price,
    }
    contract = {
        "id": product.id,
        "name": {locale: "" for locale in LOCALES},
        "tag": {locale: "" for locale in LOCALES},
        "description": {locale: "" for locale in LOCALES},
    }
    return (
        "حرّر بطاقة منتج لمنصة «نَسمة» (تجارة جمال عراقية).\n"
        "الأسلوب: هادئ، بلا مبالغة، بلا وعود medicinal أو علاجية غير مثبتة.\n"
        "لا تخترع مكونات ولا أرقاماً ولا شهادات.\n\n"
        "مدخلات:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "أعد JSON واحداً فقط بالبنية التالية (بلا نص خارج JSON):\n"
        f"{json.dumps(contract, ensure_ascii=False, indent=2)}\n"
    )


class ModelContractError(ValueError):
    """ردّ النموذج لا يطابق العقد."""


def parse_response(text: str, product: NasmaProduct) -> dict[str, Any]:
    """يحلّل ردّ النموذج ويتحقق من العقد. أي خلل ⇒ استثناء."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as error:
        raise ModelContractError(f"الردّ ليس JSON صالحاً: {error}") from error
    if not isinstance(data, dict):
        raise ModelContractError("الردّ يجب أن يكون كائن JSON.")
    for field in RESPONSE_FIELDS:
        if field not in data:
            raise ModelContractError(f"الحقل «{field}» مفقود في الردّ.")
    if str(data["id"]) != product.id:
        raise ModelContractError(
            f"معرّف المنتج في الردّ ({data['id']}) لا يطابق المطلوب ({product.id})."
        )
    for field in ("name", "tag", "description"):
        value = data[field]
        if not isinstance(value, dict):
            raise ModelContractError(f"الحقل «{field}» يجب أن يكون كائن لغات.")
        for locale in LOCALES:
            text_value = value.get(locale)
            if not isinstance(text_value, str) or not text_value.strip():
                raise ModelContractError(
                    f"الحقل «{field}» ناقص باللغة «{locale}»."
                )
    return data
