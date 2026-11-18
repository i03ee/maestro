"""منتجات البحث: منافسون، مرشّحات، وتقييم تراخيص (AC-03 وAC-04).

الشرط من وثيقة المتطلبات:
- **AC-03**: ثلاثة منافسين على الأقل، و**مصدر لكل صف**.
- **AC-04**: عدد المرشّحين أكبر من صفر، و**مصدر لكل صف**.
- **AC-05**: كل مرشّح يحمل spdx ونتيجة فحص.
- **AC-06**: كل مرشّح مقبول أو مرفوض وله سبب.

صفٌ بلا مصدر يُرفض. مصدر بلا رخصة لا يكفي. سبب بلا قرار لا يكفي.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .structured import StructuredResponseError, parse_structured

MINIMUM_COMPETITORS = 3


@dataclass(frozen=True)
class Competitor:
    """منافس واحد."""

    name: str
    url: str
    strengths: str
    weaknesses: str
    price_point: str
    source: str


@dataclass(frozen=True)
class CompetitorResult:
    """نتيجة تحليل المنافسين."""

    competitors: tuple[Competitor, ...]

    def to_csv(self) -> str:
        """جدول CSV بمصدر لكل صف."""
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["name", "url", "strengths", "weaknesses", "price_point", "source"])
        for competitor in self.competitors:
            writer.writerow(
                [
                    competitor.name,
                    competitor.url,
                    competitor.strengths,
                    competitor.weaknesses,
                    competitor.price_point,
                    competitor.source,
                ]
            )
        return buffer.getvalue()


@dataclass(frozen=True)
class Candidate:
    """مرشّح لإعادة الاستخدام."""

    name: str
    source: str
    spdx: str
    scan_result: str
    decision: str
    reason: str


@dataclass(frozen=True)
class CandidateResult:
    """نتيجة البحث عن مكونات."""

    candidates: tuple[Candidate, ...]

    def to_jsonl(self) -> str:
        """سطر لكل مرشّح."""
        lines = []
        for candidate in self.candidates:
            lines.append(
                json.dumps(
                    {
                        "name": candidate.name,
                        "source": candidate.source,
                        "spdx": candidate.spdx,
                        "scan_result": candidate.scan_result,
                        "decision": candidate.decision,
                        "reason": candidate.reason,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        return "\n".join(lines) + ("\n" if lines else "")


def validate_competitors(data: Any) -> list[str]:
    """يفحص حمولة المنافسين."""
    problems: list[str] = []
    if not isinstance(data, dict) or "competitors" not in data:
        return ["الحقل competitors مفقود."]
    competitors = data["competitors"]
    if not isinstance(competitors, list):
        return ["competitors يجب أن تكون قائمة."]
    if len(competitors) < MINIMUM_COMPETITORS:
        problems.append(f"عدد المنافسين {len(competitors)} أقل من {MINIMUM_COMPETITORS}.")
    for index, competitor in enumerate(competitors):
        if not isinstance(competitor, dict):
            problems.append(f"المنافس {index} ليس كائناً.")
            continue
        for field in ("name", "url", "source"):
            if not str(competitor.get(field, "")).strip():
                problems.append(f"المنافس {index}: الحقل «{field}» مطلوب (مصدر لكل صف).")
        for field in ("strengths", "weaknesses", "price_point"):
            if not str(competitor.get(field, "")).strip():
                problems.append(f"المنافس {index}: الحقل «{field}» مطلوب.")
    return problems


def validate_candidates(data: Any) -> list[str]:
    """يفحص حمولة المرشّحين."""
    problems: list[str] = []
    if not isinstance(data, dict) or "candidates" not in data:
        return ["الحقل candidates مفقود."]
    candidates = data["candidates"]
    if not isinstance(candidates, list):
        return ["candidates يجب أن تكون قائمة."]
    if not candidates:
        problems.append("عدد المرشّحين صفر — لا بديل عن بحث حقيقي.")
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            problems.append(f"المرشّح {index} ليس كائناً.")
            continue
        for field in ("name", "source", "spdx", "scan_result", "decision", "reason"):
            if not str(candidate.get(field, "")).strip():
                problems.append(f"المرشّح {index}: الحقل «{field}» مطلوب.")
        decision = str(candidate.get("decision", "")).strip().lower()
        if decision not in {"allow", "deny"}:
            problems.append(
                f"المرشّح {index}: القرار «{decision or '(فارغ)'}» غير معروف (allow أو deny)."
            )
    return problems


def produce_competitors(text: str) -> CompetitorResult:
    """ينتج جدول المنافسين من ردّ منظَّم."""
    data = parse_structured(text, validate_competitors)
    competitors = tuple(
        Competitor(
            name=str(item["name"]),
            url=str(item["url"]),
            strengths=str(item["strengths"]),
            weaknesses=str(item["weaknesses"]),
            price_point=str(item["price_point"]),
            source=str(item["source"]),
        )
        for item in data["competitors"]
    )
    return CompetitorResult(competitors=competitors)


def produce_candidates(text: str) -> CandidateResult:
    """ينتج قائمة المرشّحين من ردّ منظَّم."""
    data = parse_structured(text, validate_candidates)
    candidates = tuple(
        Candidate(
            name=str(item["name"]),
            source=str(item["source"]),
            spdx=str(item["spdx"]),
            scan_result=str(item["scan_result"]),
            decision=str(item["decision"]).strip().lower(),
            reason=str(item["reason"]),
        )
        for item in data["candidates"]
    )
    return CandidateResult(candidates=candidates)


def write_competitors(result: CompetitorResult, root: str | Path) -> Path:
    """يكتب `artifacts/market/competitor_matrix.csv`."""
    path = Path(root) / "artifacts" / "market" / "competitor_matrix.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.to_csv(), encoding="utf-8")
    return path


def write_candidates(result: CandidateResult, root: str | Path) -> dict[str, Path]:
    """يكتب المرشّحين وتقرير الفحص وسجل القرارات."""
    base = Path(root) / "artifacts" / "research"
    base.mkdir(parents=True, exist_ok=True)
    candidates_path = base / "candidates.jsonl"
    candidates_path.write_text(result.to_jsonl(), encoding="utf-8")

    scans_path = base / "scans" / "scan_report.json"
    scans_path.parent.mkdir(parents=True, exist_ok=True)
    scans_path.write_text(
        json.dumps(
            [
                {
                    "name": candidate.name,
                    "spdx": candidate.spdx,
                    "scan_result": candidate.scan_result,
                    "source": candidate.source,
                }
                for candidate in result.candidates
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    decisions_path = base.parent / "decisions" / "decision_log.jsonl"
    decisions_path.parent.mkdir(parents=True, exist_ok=True)
    decisions_path.write_text(
        "\n".join(
            json.dumps(
                {
                    "name": candidate.name,
                    "decision": candidate.decision,
                    "reason": candidate.reason,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            for candidate in result.candidates
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "candidates": candidates_path,
        "scans": scans_path,
        "decisions": decisions_path,
    }
