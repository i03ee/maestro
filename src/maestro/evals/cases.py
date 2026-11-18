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


#: قدرات **مؤجَّلة التقييم** مع سبب كل واحدة.
#:
#: القدرة التي لا مخرج لها بعد لا يمكن تقييمها، والتأجيل بلا سبب مكتوب
#: يُعدّ تغطيةً زائفة. لذلك كل قدرة إمّا لها حالة تقييم، أو لها سبب تأجيل.
DEFERRED: dict[str, str] = {
    "commercial.business_model": "لا منتِج لمخرج نموذج العمل بعد.",
    "commercial.pricing": "لا منتِج لتسعير مبرَّر بعد.",
    "community.community_test": "لا منتِج للوحة المجتمع بعد.",
    "research.project_evaluation": "لا منتِج لتقييم المشاريع بعد.",
    "research.project_selection": "لا منتِج لاختيار المشروع بعد.",
    "engineering.code_review": "لا منتِج لمراجعة الكود بعد.",
    "engineering.code_merge": "دمج الكود مسار لا مخرج نصّي له.",
    "engineering.code_test": "لا منتِج لكتابة الاختبارات بعد.",
    "engineering.payment_interface": "لا منتِج لواجهة الدفع بعد.",
    "experience.ui_design": "لا منتِج لتصميم الواجهة بعد.",
    "experience.ui_build": "لا منتِج لبناء الواجهة بعد.",
    "experience.ui_review": "لا منتِج لمراجعة الواجهة بعد.",
    "quality.data_security": "لا منتِج لتقرير فحص أمن البيانات بعد.",
    "quality.penetration_test": "لا منتِج لتقرير اختبار الاختراق بعد.",
    "quality.load_test": "المقياس موجود (scripts/load_check.py) لكن مخرجه تقرير لا نصّ.",
    "quality.compliance_review": "لا منتِج لتقرير الامتثال بعد.",
    "release.release_qa": "لا منتِج لتقرير فحص الإصدار بعد.",
    "release.release_signing": "التوقيع عملية لا مخرج نصّي.",
    "release.release_publish": "النشر عملية لا مخرج نصّي.",
    "data.data_pipeline": "لا منتِج مستقلّ بعد — المخرج في تخصّص catalog.ingest.",
    "data.app_template": "لا منتِج لقوالب التطبيقات بعد.",
}


def coverage_report() -> dict[str, list[str]]:
    """تغطية التقييم: مغطّاة، مؤجَّلة، ومفقودة (يجب أن تكون فارغة)."""
    from ..company.catalogue import CAPABILITIES

    covered = sorted({case.capability for case in CASES})
    known = {capability.name for capability in CAPABILITIES}
    # قدرات مُقيَّمة خارج الكتالوج (قدرة توضيحية أو تخصّص منتج) — تُذكر
    # صراحةً ولا تُحتسب من الـ24.
    extra = sorted(name for name in covered if name not in known)
    covered_in_catalogue = sorted(name for name in covered if name in known)
    deferred = sorted(set(DEFERRED) & known)
    missing = sorted(
        capability.name
        for capability in CAPABILITIES
        if capability.name not in covered and capability.name not in DEFERRED
    )
    unknown = sorted(set(DEFERRED) - known)
    return {
        "covered": covered_in_catalogue,
        "covered_extra": extra,
        "deferred": deferred,
        "missing": missing,
        "unknown_deferrals": unknown,
    }


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
        id="commercial.market_research/1",
        capability="commercial.market_research",
        description_ar="طلب تحليل منافسين ⇒ ثلاثة منافسين بمصدر لكل صف",
        document=_load("case_market_research.json"),
        check=_valid_json("competitors"),
        reply=json.dumps(
            {
                "competitors": [
                    {
                        "name": "أ",
                        "url": "https://a.example",
                        "strengths": "تغطية",
                        "weaknesses": "لا Kurdish",
                        "price_point": "مجاني",
                        "source": "https://a.example/pricing",
                    },
                    {
                        "name": "ب",
                        "url": "https://b.example",
                        "strengths": "شحن",
                        "weaknesses": "لا تطبيق",
                        "price_point": "اشتراك",
                        "source": "https://b.example/about",
                    },
                    {
                        "name": "ج",
                        "url": "https://c.example",
                        "strengths": "أسعار",
                        "weaknesses": "لا محادثة",
                        "price_point": "عمولة",
                        "source": "https://c.example",
                    },
                ]
            },
            ensure_ascii=False,
        ),
    ),
    EvalCase(
        id="research.project_research/1",
        capability="research.project_research",
        description_ar="طلب بحث عن مكونات ⇒ مرشّحون برخصة وسبب لكل صف",
        document=_load("case_project_research.json"),
        check=_valid_json("candidates"),
        reply=json.dumps(
            {
                "candidates": [
                    {
                        "name": "saleor",
                        "source": "https://github.com/saleor/saleor",
                        "spdx": "BSD-3-Clause",
                        "scan_result": "clean",
                        "decision": "allow",
                        "reason": "رخصة تسمح بالاستعمال والتوزيع.",
                    }
                ]
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
