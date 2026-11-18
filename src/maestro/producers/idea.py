"""منتج المتطلبات: من فكرة إلى PRD وقصص مستخدمين (AC-02).

الشرط من وثيقة المتطلبات: **كل ميزة «must» لها story ومعايير قبول**.
والشرط من البروتوكول: لا artefact من ردّ ناقص.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .structured import StructuredResponseError, parse_structured

PRIORITIES: tuple[str, ...] = ("must", "should", "could")


@dataclass(frozen=True)
class Feature:
    """ميزة واحدة في المتطلبات."""

    id: str
    title: str
    priority: str
    story: str
    criteria: tuple[str, ...]


@dataclass(frozen=True)
class PrdResult:
    """نتيجة إنتاج المتطلبات."""

    product_name: str
    problem: str
    features: tuple[Feature, ...]
    prd_markdown: str
    user_stories: tuple[dict[str, Any], ...]

    def as_user_stories(self) -> list[dict[str, Any]]:
        return list(self.user_stories)


def validate_prd_payload(data: Any) -> list[str]:
    """يفحص حمولة المتطلبات ويعيد المشاكل."""
    problems: list[str] = []
    if not isinstance(data, dict):
        return ["الحمولة ليست كائن JSON."]
    for field in ("product_name", "problem", "features"):
        if field not in data:
            problems.append(f"الحقل «{field}» مفقود.")
    if problems:
        return problems
    if not str(data["product_name"]).strip():
        problems.append("اسم المنتج مطلوب.")
    if not str(data["problem"]).strip():
        problems.append("المشكلة المعروضة مطلوبة.")
    features = data["features"]
    if not isinstance(features, list) or not features:
        problems.append("الحقل features يجب أن يكون قائمة غير فارغة.")
        return problems
    seen: set[str] = set()
    for index, feature in enumerate(features):
        if not isinstance(feature, dict):
            problems.append(f"الميزة {index} ليست كائناً.")
            continue
        feature_id = str(feature.get("id", "")).strip()
        if not feature_id:
            problems.append(f"الميزة {index} بلا معرّف.")
        elif feature_id in seen:
            problems.append(f"معرّف ميزة مكرر: {feature_id}.")
        seen.add(feature_id)
        if not str(feature.get("title", "")).strip():
            problems.append(f"الميزة {feature_id or index} بلا عنوان.")
        priority = str(feature.get("priority", "")).strip().lower()
        if priority not in PRIORITIES:
            problems.append(
                f"أولوية الميزة {feature_id or index} غير معروفة: {priority or '(فارغة)'}."
            )
        if not str(feature.get("story", "")).strip():
            problems.append(f"الميزة {feature_id or index} بلا story.")
        criteria = feature.get("criteria")
        if not isinstance(criteria, list) or not criteria:
            problems.append(f"الميزة {feature_id or index} بلا معايير قبول.")
        elif not all(isinstance(item, str) and item.strip() for item in criteria):
            problems.append(f"معايير قبول الميزة {feature_id or index} فيها فراغ.")
    return problems


def produce_prd(text: str) -> PrdResult:
    """ينتج المتطلبات من ردّ منظَّم."""
    data = parse_structured(text, validate_prd_payload)
    features: list[Feature] = []
    stories: list[dict[str, Any]] = []
    for feature in data["features"]:
        criteria = tuple(str(item) for item in feature["criteria"])
        features.append(
            Feature(
                id=str(feature["id"]),
                title=str(feature["title"]),
                priority=str(feature["priority"]).strip().lower(),
                story=str(feature["story"]),
                criteria=criteria,
            )
        )
        stories.append(
            {
                "id": str(feature["id"]),
                "title": str(feature["title"]),
                "priority": str(feature["priority"]).strip().lower(),
                "story": str(feature["story"]),
                "acceptance_criteria": list(criteria),
            }
        )

    must = [feature for feature in features if feature.priority == "must"]
    lines: list[str] = []
    lines.append(f"# {data['product_name']}")
    lines.append("")
    lines.append("## المشكلة")
    lines.append("")
    lines.append(str(data["problem"]))
    lines.append("")
    lines.append("## الميزات")
    lines.append("")
    for feature in features:
        lines.append(f"### {feature.id} — {feature.title}")
        lines.append("")
        lines.append(f"- الأولوية: {feature.priority}")
        lines.append(f"- القصة: {feature.story}")
        for criterion in feature.criteria:
            lines.append(f"  - معيار القبول: {criterion}")
        lines.append("")
    lines.append(f"عدد الميزات: {len(features)} (منها {len(must)} بمعيار must).")
    lines.append("")
    prd_markdown = "\n".join(lines)

    return PrdResult(
        product_name=str(data["product_name"]),
        problem=str(data["problem"]),
        features=tuple(features),
        prd_markdown=prd_markdown,
        user_stories=tuple(stories),
    )


def write_prd(result: PrdResult, root: str | Path) -> dict[str, Path]:
    """يكتب `artifacts/prd.md` و`artifacts/user_stories.json`."""
    base = Path(root)
    artifacts = base / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    prd_path = artifacts / "prd.md"
    stories_path = artifacts / "user_stories.json"
    prd_path.write_text(result.prd_markdown, encoding="utf-8")
    stories_path.write_text(
        json.dumps(result.as_user_stories(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"prd": prd_path, "user_stories": stories_path}
