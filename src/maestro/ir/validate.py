"""محرّك قواعد الـIR: يحوّل مستند مهمة إلى قائمة ملاحظات حتمية.

قاعدة التصميم: كل قاعدة تُرجع «نعم/لا» لا «احتمال». لا نسب خطأ، ولا عتبات
نسبية، ولا استثناءات متسامحة. مستند يجتاز كل القواعد يُعتمد، وإلا يُرفض
مع ذكر القاعدة المكسورة.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from ..version import SUPPORTED_IR_VERSIONS
from .rules import RULES_BY_ID, rule_ids

CAPABILITY_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)+$")
ROLE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")

#: الأدوات المسموحة. أي أداة خارج هذه القائمة تُرفض عند IR-08.
ALLOWED_TOOLS: frozenset[str] = frozenset(
    {
        "fs.read",
        "fs.write",
        "http.get",
        "http.post",
        "saleor.graphql",
        "model.generate",
        "render.image",
        "vector.search",
        "git.read",
    }
)

#: سقف التكلفة العام لمهمة واحدة (دولار أمريكي).
GLOBAL_MAX_COST_USD = 5.0
#: سقف الرموز العام لمهمة واحدة.
GLOBAL_MAX_TOKENS = 200_000
#: أقصى عدد خطوات في مهمة واحدة.
MAX_STEPS = 25
#: أقصى مهلة (ثوانٍ) للقدرات الحرجة.
CRITICAL_MAX_WALL_SECONDS = 300
#: القدرات التي لا يُقبل تنفيذها بلا تكرار نماذج ودليل موثّق.
CRITICAL_CAPABILITIES: frozenset[str] = frozenset(
    {
        "catalog.ingest",
        "payment.capture",
        "pricing.update",
        "security.review",
        "release.publish",
    }
)

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*['\"]?\S{8,}"),
)


@dataclass(frozen=True)
class Finding:
    """ملاحظة واحدة عن مستند IR."""

    rule_id: str
    severity: str
    message_ar: str
    path: str

    def as_dict(self) -> dict[str, str]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message_ar": self.message_ar,
            "path": self.path,
        }


def _finding(rule_id: str, message: str, path: str) -> Finding:
    rule = RULES_BY_ID[rule_id]
    return Finding(rule_id=rule.id, severity=rule.severity, message_ar=message, path=path)


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


# --------------------------------------------------------------------------
# القواعد
# --------------------------------------------------------------------------


def _check_ir01(doc: dict[str, Any]) -> list[Finding]:
    version = doc.get("ir_version")
    if version not in SUPPORTED_IR_VERSIONS:
        return [
            _finding(
                "IR-01",
                f"إصدار IR غير مدعوم: {version!r}؛ المدعوم: {', '.join(SUPPORTED_IR_VERSIONS)}.",
                "ir_version",
            )
        ]
    return []


def _check_ir02(doc: dict[str, Any]) -> list[Finding]:
    capability = doc.get("capability")
    if not isinstance(capability, str) or not CAPABILITY_PATTERN.match(capability):
        return [
            _finding(
                "IR-02",
                "معرّف القدرة يجب أن يكون متدرّجاً بأحرف صغيرة، مثل catalog.ingest أو commercial.idea_framing.",
                "capability",
            )
        ]
    return []


def _check_ir03(doc: dict[str, Any]) -> list[Finding]:
    intent = doc.get("intent")
    if not isinstance(intent, str) or not intent.strip():
        return [_finding("IR-03", "النيّة مطلوبة ويجب أن تكون نصاً غير فارغ.", "intent")]
    if len(intent.strip()) < 8:
        return [_finding("IR-03", "النيّة قصيرة جداً؛ يجب أن تصف المطلوب تبويباً واحداً على الأقل.", "intent")]
    if len(intent) > 2000:
        return [_finding("IR-03", "النيّة أطول من 2000 حرف؛ قسّم المهمة.", "intent")]
    return []


def _check_ir04(doc: dict[str, Any]) -> list[Finding]:
    authority = doc.get("authority")
    if isinstance(authority, bool) or not isinstance(authority, int) or authority not in (1, 2, 3):
        return [
            _finding(
                "IR-04",
                "مستوى الصلاحية يجب أن يكون عدداً صحيحاً ضمن 1..3.",
                "authority",
            )
        ]
    if authority >= 3 and doc.get("human_approval") is not True:
        return [
            _finding(
                "IR-04",
                "الصلاحية 3 تتطلب موافقة بشرية مسجّلة قبل التنفيذ.",
                "human_approval",
            )
        ]
    return []


def _check_ir05(doc: dict[str, Any]) -> list[Finding]:
    steps = doc.get("steps")
    if not isinstance(steps, list) or not steps:
        return [_finding("IR-05", "المهمة تحتاج خطوة واحدة على الأقل.", "steps")]
    if len(steps) > MAX_STEPS:
        return [
            _finding(
                "IR-05",
                f"عدد الخطوات {len(steps)} يتجاوز الحد {MAX_STEPS}؛ قسّم المهمة.",
                "steps",
            )
        ]
    return []


def _check_ir06(doc: dict[str, Any]) -> list[Finding]:
    steps = doc.get("steps")
    if not isinstance(steps, list):
        return []
    seen: set[str] = set()
    findings: list[Finding] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        step_id = step.get("id")
        if not isinstance(step_id, str) or not step_id:
            continue
        if step_id in seen:
            findings.append(
                _finding("IR-06", f"معرّف خطوة مكرر: {step_id}.", f"steps[{index}].id")
            )
        seen.add(step_id)
    return findings


def _check_ir07(doc: dict[str, Any]) -> list[Finding]:
    steps = doc.get("steps")
    if not isinstance(steps, list):
        return []
    findings: list[Finding] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            findings.append(
                _finding("IR-07", "الخطوة ليست كائناً.", f"steps[{index}]")
            )
            continue
        agent = step.get("agent")
        if not isinstance(agent, str) or not ROLE_PATTERN.match(agent):
            findings.append(
                _finding(
                    "IR-07",
                    "كل خطوة تعلن وكيلاً بمعرّف صالح مثل catalog_writer.",
                    f"steps[{index}].agent",
                )
            )
    return findings


def _check_ir08(doc: dict[str, Any]) -> list[Finding]:
    steps = doc.get("steps")
    if not isinstance(steps, list):
        return []
    findings: list[Finding] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        tools = step.get("tools", [])
        if not isinstance(tools, list):
            findings.append(
                _finding("IR-08", "قائمة الأدوات يجب أن تكون مصفوفة.", f"steps[{index}].tools")
            )
            continue
        for tool in tools:
            if tool not in ALLOWED_TOOLS:
                findings.append(
                    _finding(
                        "IR-08",
                        f"أداة خارج القائمة المسموحة: {tool}.",
                        f"steps[{index}].tools",
                    )
                )
    return findings


def _check_ir09(doc: dict[str, Any]) -> list[Finding]:
    budget = doc.get("budget")
    if not isinstance(budget, dict):
        return [_finding("IR-09", "ميزانية المهمة مطلوبة.", "budget")]
    findings: list[Finding] = []
    tokens = _as_number(budget.get("max_tokens"))
    cost = _as_number(budget.get("max_cost_usd"))
    wall = _as_number(budget.get("max_wall_seconds"))
    if tokens is None or tokens <= 0:
        findings.append(_finding("IR-09", "max_tokens يجب أن يكون عدداً موجباً.", "budget.max_tokens"))
    elif tokens > GLOBAL_MAX_TOKENS:
        findings.append(
            _finding(
                "IR-09",
                f"max_tokens {int(tokens)} يتجاوز السقف العام {GLOBAL_MAX_TOKENS}.",
                "budget.max_tokens",
            )
        )
    if cost is None or cost <= 0:
        findings.append(_finding("IR-09", "max_cost_usd يجب أن يكون عدداً موجباً.", "budget.max_cost_usd"))
    elif cost > GLOBAL_MAX_COST_USD:
        findings.append(
            _finding(
                "IR-09",
                f"max_cost_usd {cost} يتجاوز السقف العام {GLOBAL_MAX_COST_USD}.",
                "budget.max_cost_usd",
            )
        )
    if wall is None or wall <= 0:
        findings.append(
            _finding("IR-09", "max_wall_seconds يجب أن يكون عدداً موجباً.", "budget.max_wall_seconds")
        )
    return findings


def _check_ir10(doc: dict[str, Any]) -> list[Finding]:
    budget = doc.get("budget")
    steps = doc.get("steps")
    if not isinstance(budget, dict) or not isinstance(steps, list):
        return []
    doc_tokens = _as_number(budget.get("max_tokens")) or 0.0
    doc_cost = _as_number(budget.get("max_cost_usd")) or 0.0
    findings: list[Finding] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        step_budget = step.get("budget")
        if not isinstance(step_budget, dict):
            continue
        step_tokens = _as_number(step_budget.get("max_tokens"))
        step_cost = _as_number(step_budget.get("max_cost_usd"))
        if step_tokens is not None and step_tokens > doc_tokens:
            findings.append(
                _finding(
                    "IR-10",
                    f"ميزانية رموز الخطوة ({int(step_tokens)}) تتجاوز ميزانية المهمة ({int(doc_tokens)}).",
                    f"steps[{index}].budget.max_tokens",
                )
            )
        if step_cost is not None and step_cost > doc_cost:
            findings.append(
                _finding(
                    "IR-10",
                    f"ميزانية تكلفة الخطوة ({step_cost}) تتجاوز ميزانية المهمة ({doc_cost}).",
                    f"steps[{index}].budget.max_cost_usd",
                )
            )
    return findings


def _is_critical(doc: dict[str, Any]) -> bool:
    capability = doc.get("capability")
    if doc.get("critical") is True:
        return True
    return isinstance(capability, str) and capability in CRITICAL_CAPABILITIES


def _check_ir11(doc: dict[str, Any]) -> list[Finding]:
    if not _is_critical(doc):
        return []
    budget = doc.get("budget")
    if not isinstance(budget, dict):
        return []
    wall = _as_number(budget.get("max_wall_seconds"))
    if wall is None:
        return [_finding("IR-11", "القدرة الحرجة تحتاج مهلة زمنية محددة.", "budget.max_wall_seconds")]
    if wall > CRITICAL_MAX_WALL_SECONDS:
        return [
            _finding(
                "IR-11",
                f"مهلة القدرة الحرجة ({int(wall)} ث) تتجاوز الحد {CRITICAL_MAX_WALL_SECONDS} ث.",
                "budget.max_wall_seconds",
            )
        ]
    return []


def _check_ir12(doc: dict[str, Any]) -> list[Finding]:
    if not _is_critical(doc):
        return []
    redundancy = doc.get("redundancy")
    if not isinstance(redundancy, dict):
        return [_finding("IR-12", "القدرة الحرجة تحتاج كتلة redundancy.", "redundancy")]
    findings: list[Finding] = []
    ensemble = redundancy.get("ensemble")
    if not isinstance(ensemble, list) or len(ensemble) < 2:
        findings.append(
            _finding(
                "IR-12",
                "القدرة الحرجة تحتاج نموذجين على الأقل في مجموعة التكرار.",
                "redundancy.ensemble",
            )
        )
    agreement = redundancy.get("min_agreement")
    if not isinstance(agreement, int) or isinstance(agreement, bool) or agreement < 2:
        findings.append(
            _finding(
                "IR-12",
                "القدرة الحرجة تحتاج اتفاق نموذجين (min_agreement = 2 فأكثر).",
                "redundancy.min_agreement",
            )
        )
    return findings


def _check_ir13(doc: dict[str, Any]) -> list[Finding]:
    if not _is_critical(doc):
        return []
    evidence = doc.get("evidence")
    if not isinstance(evidence, dict):
        return [_finding("IR-13", "القدرة الحرجة تحتاج كتلة evidence.", "evidence")]
    findings: list[Finding] = []
    if evidence.get("required") is not True:
        findings.append(
            _finding("IR-13", "الدليل إلزامي في القدرات الحرجة.", "evidence.required")
        )
    artifacts = evidence.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        findings.append(
            _finding("IR-13", "يجب تحديد دليل واحد على الأقل يُنتج مع المهمة.", "evidence.artifacts")
        )
    return findings


def _check_ir14(doc: dict[str, Any]) -> list[Finding]:
    inputs = doc.get("inputs", {})
    try:
        payload = json.dumps(inputs, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return [_finding("IR-14", "المدخلات غير قابلة للترميز.", "inputs")]
    findings: list[Finding] = []
    for pattern in SECRET_PATTERNS:
        match = pattern.search(payload)
        if match:
            findings.append(
                _finding(
                    "IR-14",
                    "المدخلات تحتوي على قيمة تشبه سرّاً؛ انقلها إلى مدير الأسرار.",
                    "inputs",
                )
            )
            break
    return findings


CHECKS: dict[str, Callable[[dict[str, Any]], list[Finding]]] = {
    "IR-01": _check_ir01,
    "IR-02": _check_ir02,
    "IR-03": _check_ir03,
    "IR-04": _check_ir04,
    "IR-05": _check_ir05,
    "IR-06": _check_ir06,
    "IR-07": _check_ir07,
    "IR-08": _check_ir08,
    "IR-09": _check_ir09,
    "IR-10": _check_ir10,
    "IR-11": _check_ir11,
    "IR-12": _check_ir12,
    "IR-13": _check_ir13,
    "IR-14": _check_ir14,
}


def validate_ir(doc: dict[str, Any]) -> list[Finding]:
    """يفحص مستند مهمة ويعيد كل الملاحظات بالترتيب الثابت للقواعد."""
    if not isinstance(doc, dict):
        return [_finding("IR-01", "المستند ليس كائن JSON.", "$")]
    findings: list[Finding] = []
    for rule_id in rule_ids():
        check = CHECKS.get(rule_id)
        if check is None:
            raise RuntimeError(f"قاعدة بلا فحص: {rule_id}")
        findings.extend(check(doc))
    return findings


def is_valid_ir(doc: dict[str, Any]) -> bool:
    """مستند صالح = لا ملاحظة من نوع error."""
    return not any(finding.severity == "error" for finding in validate_ir(doc))


def errors_only(findings: Iterable[Finding]) -> list[Finding]:
    """يستخرج الملاحظات الحاجبة فقط."""
    return [finding for finding in findings if finding.severity == "error"]
