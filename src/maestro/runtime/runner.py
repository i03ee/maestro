"""مُشغّل القدرة: يمرّر المهمة عبر كل البوابات بالترتيب.

الترتيب ثابت: عقد IR ← سجل القدرات ← الصلاحيات ← الميزانية ← التوجيه ←
الدليل. أول بوابة ترفض تُوقف المسار وتُعيد سبباً مكتوباً. لا مسار «تجاوز»
ولا تسامح.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any

from ..evidence.log import EvidenceLog
from ..guards.budget import BudgetExceeded, BudgetGuard
from ..guards.permission import PermissionGuard
from ..ir.validate import Finding, errors_only, validate_ir
from ..routing.base import CompletionRequest
from ..routing.router import Attempt, ModelRouter, RoutingFailure
from .registry import CapabilityRegistry


@dataclass(frozen=True)
class ExecutionReport:
    """تقرير تنفيذ قدرة: نجح أم رُفض، وأين، ولماذا."""

    capability: str
    ok: bool
    stage: str
    detail_ar: str
    output: str | None = None
    findings: tuple[Finding, ...] = ()
    attempts: tuple[Attempt, ...] = ()
    evidence_hash: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "ok": self.ok,
            "stage": self.stage,
            "detail_ar": self.detail_ar,
            "output": self.output,
            "findings": [f.as_dict() for f in self.findings],
            "attempts": [a.as_dict() for a in self.attempts],
            "evidence_hash": self.evidence_hash,
        }


def _context_of(inputs: object) -> str:
    """يحوّل `inputs` من مستند IR إلى سياق نصّي للمطالبة."""
    if not inputs:
        return ""
    if isinstance(inputs, str):
        return inputs
    return json.dumps(inputs, ensure_ascii=False, indent=2, sort_keys=True)


class CapabilityRunner:
    """يشغّل قدرة واحدة عبر كل البوابات."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        router: ModelRouter,
        permissions: PermissionGuard,
        evidence: EvidenceLog | None = None,
    ):
        self.registry = registry
        self.router = router
        self.permissions = permissions
        self.evidence = evidence

    def run(self, doc: dict[str, Any]) -> ExecutionReport:
        """ينفّذ مستند مهمة ويعيد تقريراً كاملاً."""
        capability = str(doc.get("capability", ""))

        findings = errors_only(validate_ir(doc))
        if findings:
            return ExecutionReport(
                capability=capability,
                ok=False,
                stage="ir",
                detail_ar=f"مستند المهمة رُفض: {findings[0].message_ar}",
                findings=tuple(findings),
            )

        spec = self.registry.get(capability)
        if spec is None:
            return ExecutionReport(
                capability=capability,
                ok=False,
                stage="registry",
                detail_ar=f"القدرة غير مسجّلة: {capability}.",
            )

        authority = int(doc.get("authority", spec.default_authority))
        decision = self.permissions.authorize(
            capability,
            authority,
            human_approved=doc.get("human_approval") is True,
        )
        if not decision.allowed:
            return ExecutionReport(
                capability=capability,
                ok=False,
                stage="permission",
                detail_ar=decision.reason_ar,
            )

        doc_budget = doc.get("budget", {})
        budget = BudgetGuard(
            max_cost_usd=float(doc_budget.get("max_cost_usd", 1.0)),
            max_tokens=int(doc_budget.get("max_tokens", 100_000)),
        )
        scoped = replace(self.router, budget=budget)
        # سقف الإخراج يُشتقّ من ميزانية المهمة: مهمة بميزانية 1000 رمز لا
        # تستطيع أن تطلب 1024 رمز إخراج. الافتراضي 1024 أو ميزانية المهمة
        # أيهما أصغر، ويمكن تجاوزه صراحةً بـmax_output_tokens.
        default_output = min(1024, int(doc_budget.get("max_tokens", 1024)))
        request = CompletionRequest(
            capability=capability,
            prompt=spec.render_prompt(
                str(doc.get("intent", "")), _context_of(doc.get("inputs"))
            ),
            max_output_tokens=int(doc_budget.get("max_output_tokens", default_output)),
            tools=tuple(spec.required_tools),
            authority=authority,
        )

        try:
            result = scoped.run(request)
        except BudgetExceeded as error:
            return ExecutionReport(
                capability=capability,
                ok=False,
                stage="budget",
                detail_ar=str(error),
            )
        except RoutingFailure as error:
            return ExecutionReport(
                capability=capability,
                ok=False,
                stage="routing",
                detail_ar=str(error),
                attempts=error.attempts,
            )

        evidence_hash = None
        if self.evidence is not None:
            evidence_hash = self.evidence.append(
                "capability",
                {
                    "capability": capability,
                    "authority": authority,
                    "critical": spec.critical,
                    "declared_ensemble": doc.get("redundancy", {}).get("ensemble", []),
                    "min_agreement": doc.get("redundancy", {}).get("min_agreement"),
                    "attempts": [a.as_dict() for a in result.attempts],
                    "cost_usd": result.cost_usd,
                    "output_sha256_hint": len(result.text),
                },
            )

        return ExecutionReport(
            capability=capability,
            ok=True,
            stage="done",
            detail_ar="نُفِّذت القدرة واجتازت كل البوابات.",
            output=result.text,
            attempts=result.attempts,
            evidence_hash=evidence_hash,
        )
