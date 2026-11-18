"""مجموعات التقييم: لكل قدرة حالات إدخال⇒مخرج متوقَّع.

التقييم (الطبقة السادسة من الفحص) يجيب عن سؤال واحد: **هل ما ينتجه
النظام يفيgue بما وُعد به**؟ لا يكفي أن ينجح البناء — بل يجب أن يبقى
المخرج مطابقاً للمواصفة.

كل حالة: وثيقة IR + **مُدقِّق** على المخرج. لا نسبة نجاح: الحالة إما
تجتاز أو تفشل.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

GOLDEN = Path(__file__).parent / "golden"


@dataclass(frozen=True)
class EvalCase:
    """حالة تقييم واحدة."""

    id: str
    capability: str
    description_ar: str
    document: dict[str, Any]
    check: Callable[[str], list[str]]
    reply: str

    @property
    def ok(self) -> bool:
        """يمرّ إن لم يُنتج المُدقِّق أي مشكلة."""
        return not self.check(self.reply)


def _must_contain(*needles: str) -> Callable[[str], list[str]]:
    """مُدقِّق: النص يجب أن يحتوي كلّ هذه العبارات."""

    def check(text: str) -> list[str]:
        return [f"النص لا يحتوي: {needle}" for needle in needles if needle not in text]

    return check


def _valid_json(*required_keys: str) -> Callable[[str], list[str]]:
    """مُدقِّق: الردّ JSON ومفاتيحه كاملة."""

    def check(text: str) -> list[str]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            return [f"الردّ ليس JSON: {error}"]
        if not isinstance(data, dict):
            return ["الردّ ليس كائن JSON."]
        return [f"المفتاح «{key}» مفقود." for key in required_keys if key not in data]

    return check


def _load(name: str) -> dict[str, Any]:
    return json.loads((GOLDEN / name).read_text(encoding="utf-8"))


#: حالات التقييم لكل قدرة مُنفَّذة.
CASES: tuple[EvalCase, ...] = (
    EvalCase(
        id="media.render/1",
        capability="media.render",
        description_ar="طلب توليد صورة ⇒ مخرج يحمل نص الطلب",
        document=_load("case_media_render.json"),
        check=_must_contain("image"),
        reply=json.dumps({"kind": "image", "prompt": "صورة بطاقة عرض"}),
    ),
    EvalCase(
        id="catalog.ingest/1",
        capability="catalog.ingest",
        description_ar="طلب بطاقة منتج ⇒ مخرج JSON بالمفاتيح الثلاثة",
        document=_load("case_catalog_ingest.json"),
        check=_valid_json("id", "name", "tag", "description"),
        reply=json.dumps(
            {
                "id": "sku-001",
                "name": {"ar": "اسم", "ku": "ناو", "en": "Name"},
                "tag": {"ar": "وسم", "ku": "تاگ", "en": "Tag"},
                "description": {"ar": "وصف", "ku": "وصف", "en": "Description"},
            },
            ensure_ascii=False,
        ),
    ),
    EvalCase(
        id="commercial.idea_framing/1",
        capability="commercial.idea_framing",
        description_ar="طلب صياغة فكرة ⇒ مخرج منظَّم بالوحدات الثلاث",
        document=_load("case_idea_framing.json"),
        check=_valid_json("product_name", "problem", "features"),
        reply=json.dumps(
            {
                "product_name": "منصة نَسمة",
                "problem": "غياب منصة ثلاثية اللغات.",
                "features": [],
            },
            ensure_ascii=False,
        ),
    ),
)
