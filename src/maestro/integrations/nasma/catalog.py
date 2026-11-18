"""شكل المنتج في نَسمة: نفس بنية الكتالوج في التطبيقين.

المصدر: `packages/core/src/catalog.mjs` في مستودع نَسمة. أُعيدت هذه الكتابة
بلغة بايثون مع نفس القواعد (تنسيق الدينار بثلاث لغات، تقييد روابط الصور،
قائمة اللغات) — بلا نسخ حرفي: القواعد سلوكٌ مُعاد بنفس المعنى.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

LOCALES: tuple[str, ...] = ("ar", "ku", "en")

#: نبرة العرض في نَسمة: عنوان هادئ بلا مبالغة ولا وعود غير مثبتة.
TONES: tuple[str, ...] = ("rose", "sand", "sage", "lavender")


#: الأرقام العربية-الهندية، كما يعرضها `Intl.NumberFormat('ar-IQ')` في نَسمة.
ARABIC_INDIC_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def format_iqd(value: int, locale: str = "ar") -> str:
    """تنسيق المبلغ بالدينار العراقي: أرقام عربية-هندية بلا كسور.

    نفس سلوك `formatIQD` في `packages/core/src/catalog.mjs` من نَسمة:
    `ar` و`ku` بأرقام عربية-هندية وفاصل `٬`، و`en` بأرقام لاتينية و`IQD`.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("المبلغ يجب أن يكون عدداً صحيحاً غير سالب")
    if locale == "en":
        return f"{value:,} IQD"
    grouped = f"{value:,}".replace(",", "٬")
    return f"{grouped.translate(ARABIC_INDIC_DIGITS)} د.ع"


def safe_image(value: str | None) -> str | None:
    """رابط صورة آمن: http/https فقط."""
    if not value:
        return None
    try:
        parsed = urlparse(value)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"}:
        return None
    return value


@dataclass(frozen=True)
class NasmaProduct:
    """منتج واحد جاهز للكتالوج، بثلاث لغات."""

    id: str
    names: dict[str, str]
    categories: dict[str, str]
    price: int
    slug: str
    image: str | None = None
    image_alt: str | None = None
    tags: dict[str, str] | None = None
    tone: str = "rose"

    def to_catalog_entry(self) -> dict[str, Any]:
        """الشكل الذي تستهلكه واجهة نَسمة (`/api/catalog`)."""
        return {
            "id": self.id,
            "name": dict(self.names),
            "category": dict(self.categories),
            "price": self.price,
            "slug": self.slug,
            "image": self.image,
            "imageAlt": self.image_alt or self.names.get("ar", ""),
            "tag": dict(self.tags or {}),
            "tone": self.tone,
        }


def validate_product(product: NasmaProduct) -> list[str]:
    """يفحص منتجاً ويعيد قائمة الأخطاء بالعربية (فارغة = سليم)."""
    problems: list[str] = []
    if not product.id.strip():
        problems.append("المعرّف مطلوب.")
    for locale in LOCALES:
        if not product.names.get(locale, "").strip():
            problems.append(f"الاسم بـ«{locale}» مطلوب.")
        if not product.categories.get(locale, "").strip():
            problems.append(f"التصنيف بـ«{locale}» مطلوب.")
    if isinstance(product.price, bool) or not isinstance(product.price, int) or product.price < 0:
        problems.append("السعر يجب أن يكون عدداً صحيحاً غير سالب بالدينار.")
    if not product.slug.strip():
        problems.append("المعرّف النصي (slug) مطلوب.")
    if product.image is not None and safe_image(product.image) is None:
        problems.append("رابط الصورة غير آمن.")
    if product.tone not in TONES:
        problems.append(f"نبرة العرض غير معروفة: {product.tone}.")
    return problems


def load_supplier_rows(path: str | Path) -> list[dict[str, str]]:
    """يقرأ ملف مورّد (JSON أو CSV) ويعيد أسطره."""
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    if file_path.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, dict):
            data = data.get("products", [])
        if not isinstance(data, list):
            raise ValueError("ملف JSON يجب أن يحوي قائمة منتجات.")
        return [dict(row) for row in data]
    if file_path.suffix.lower() == ".csv":
        return [dict(row) for row in csv.DictReader(text.splitlines())]
    raise ValueError(f"صيغة غير مدعومة: {file_path.suffix}")


def product_from_row(row: dict[str, Any]) -> NasmaProduct:
    """يحوّل سطر مورّد إلى منتج، مع تنسيق أوضاع الفيديو المتاحة."""
    names = {
        locale: str(row.get(f"name_{locale}") or row.get(f"name-{locale}") or "").strip()
        for locale in LOCALES
    }
    categories = {
        locale: str(row.get(f"category_{locale}") or row.get(f"category-{locale}") or "").strip()
        for locale in LOCALES
    }
    tags = {
        locale: str(row.get(f"tag_{locale}") or row.get(f"tag-{locale}") or "").strip()
        for locale in LOCALES
    }
    price_raw = row.get("price", 0)
    try:
        price = int(str(price_raw).strip())
    except (TypeError, ValueError):
        price = -1
    return NasmaProduct(
        id=str(row.get("id", "")).strip(),
        names=names,
        categories=categories,
        price=price,
        slug=str(row.get("slug", "") or row.get("id", "")).strip(),
        image=safe_image(row.get("image")),
        image_alt=str(row.get("image_alt", "")).strip() or None,
        tags=tags or None,
        tone=str(row.get("tone", "rose")).strip() or "rose",
    )
