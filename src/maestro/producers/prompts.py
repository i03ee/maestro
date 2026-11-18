"""مطالبات المنتجَين الحيّين: الفكرة→متطلبات، والسوق→منافسون، والحاجة→مرشّحون.

لكل قدرة **مطالبة واحدة** مكتوبة صراحةً، و**مُدقِّق** واحد يتحقّق من الردّ.
المطالبة تُعيد JSON وحده: لا نصّ حرف حوله، لا شرح، لا اعتذار.

القاعدة التي تلتزم بها المطالبات:
- **لا اختراع**: ما لا تعرفه يُكتب «غير معروف» — وهو أصدق من قيمة مخترعة.
- **المصدر لكل صف**: كل منافس ومرشّح بلا مصدر ⇒ يُرفض الردّ كله.
- **الترخيص حقيقي**: SPDX حقيقي، والقرار مبنيّ على قاعدة «نقبل الكود، نرفض
  الترخيص» (ADR 0004).
"""

from __future__ import annotations

import json
from typing import Any, Callable

from .idea import PRIORITIES, validate_prd_payload
from .research import validate_candidates, validate_competitors

Validator = Callable[[Any], list[str]]


def prd_prompt(payload: dict[str, Any]) -> str:
    """مطالبة تحويل فكرة إلى متطلبات."""
    idea = str(payload.get("idea", "")).strip()
    product_hint = str(payload.get("product_name", "")).strip()
    contract = {
        "product_name": product_hint or "اسم المنتج",
        "problem": "المشكلة المعروضة في سطرين",
        "features": [
            {
                "id": "F1",
                "title": "عنوان الميزة",
                "priority": "must",
                "story": "بصيغة: كـ<دور> أريد <قدرة> كي <فائدة>",
                "criteria": ["معيار قبول قابل للتحقّق"],
            }
        ],
    }
    return (
        "أنت مُنتج متطلبات في شركة برمجية صغيرة. مهمتك: تحويل فكرة إلى متطلبات "
        "قابلة للتنفيذ.\n\n"
        "الفكرة:\n"
        f"{idea}\n\n"
        "قواعد:\n"
        f"- الأولويات المسموحة: {'، '.join(PRIORITIES)}.\n"
        "- كل ميزة «must» لها story بصيغة: كـ<دور> أريد <قدرة> كي <فائدة>.\n"
        "- كل ميزة لها **معايير قبول قابلة للتحقّق** (شيء يمكن فحصه آلياً أو "
        "بقرار بشري موثّق، لا «يعمل جيداً»).\n"
        "- المعرّفات فريدة ومتسلسلة: F1، F2، ...\n"
        "- من خمس إلى سبع ميزات: الردّ المقطوع يعني artefact مرفوض.\n"
        "- لا تختلق أرقاماً ولا أسماء عملاء ولا مواعيد.\n\n"
        "أعد JSON واحداً فقط بالبنية التالية (بلا نصّ خارج JSON):\n"
        f"{json.dumps(contract, ensure_ascii=False, indent=2)}\n"
    )


def competitors_prompt(payload: dict[str, Any]) -> str:
    """مطالبة تحليل سوق."""
    market = str(payload.get("market", "")).strip()
    contract = {
        "competitors": [
            {
                "name": "اسم المنافس",
                "url": "https://...",
                "strengths": "نقاط القوة",
                "weaknesses": "نقاط الضعف",
                "price_point": "نطاق السعر أو «غير معروف»",
                "source": "المصدر: رابط صفحة الأسعار أو وصف واضح لمصدر المعلومة",
            }
        ]
    }
    return (
        "أنت محلّل سوق في شركة برمجية صغيرة. مهمتك: بناء جدول منافسين موثّق.\n\n"
        "السوق:\n"
        f"{market}\n\n"
        "قواعد:\n"
        "- من ثلاثة إلى خمسة منافسين (لا أكثر: الردّ المقطوع يُرفض).\n"
        "- **لكل صف مصدر**: رابط أو وصف واضح لمصدر المعلومة. بلا مصدر ⇒ ردّ مرفوض.\n"
        "- إن لم تعرف سعراً أو رابطاً فاكتب «غير معروف» بدل الاختراع.\n"
        "- لا تختلق نطاقات مواقع.\n\n"
        "أعد JSON واحداً فقط بالبنية التالية (بلا نصّ خارج JSON):\n"
        f"{json.dumps(contract, ensure_ascii=False, indent=2)}\n"
    )


def candidates_prompt(payload: dict[str, Any]) -> str:
    """مطالبة بحث مكونات جاهزة لإعادة الاستخدام."""
    need = str(payload.get("need", "")).strip()
    contract = {
        "candidates": [
            {
                "name": "اسم المشروع",
                "source": "https://github.com/...",
                "spdx": "MIT",
                "scan_result": "clean",
                "decision": "allow",
                "reason": "سبب القرار في جملة",
            }
        ]
    }
    return (
        "أنت باحث مكونات في شركة برمجية صغيرة. مهمتك: اقتراح مشاريع مفتوحة "
        "المصدر يمكن إعادة استخدام كودها.\n\n"
        "الحاجة:\n"
        f"{need}\n\n"
        "قواعد:\n"
        "- اذكر مشاريع **موجودة فعلاً** ومعروفة. لا تختلق مستودعات.\n"
        "- `spdx` هو معرّف الترخيص الحقيقي (MIT، Apache-2.0، BSD-3-Clause، ...).\n"
        "- القرار `allow` للتراخيص المتوافقة مع OSI و«نقبل الكود، نرفض الترخيص»؛ "
        "و`deny` لغيرها (GPL، AGPL، FSL، ترخيص مقيّد) مع سبب.\n"
        "- `scan_result` إمّا `clean` أو `flagged` مع سبب الفحص.\n"
        "- كل صف يحتاج `source` و`reason`.\n\n"
        "أعد JSON واحداً فقط بالبنية التالية (بلا نصّ خارج JSON):\n"
        f"{json.dumps(contract, ensure_ascii=False, indent=2)}\n"
    )


#: (المطالبة، المُدقِّق) لكل قدرة حيّة.
PROMPT_BUILDERS: dict[str, tuple[Callable[[dict[str, Any]], str], Validator]] = {
    "idea.prd": (prd_prompt, validate_prd_payload),
    "research.competitors": (competitors_prompt, validate_competitors),
    "research.candidates": (candidates_prompt, validate_candidates),
}
