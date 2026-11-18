"""معايير القبول AC-01..AC-20 ودليل تنفيذها.

المعايير كما وردت في وثيقة المتطلبات (§20)، ولكل معيار:
- **الدليل المسمّى**: artefact يُنتَج في المسار المحدّد.
- **الاختبار الآلي**: فحص يمرّ أو يفشل — بلا «نسبة نجاح».

الحالة لكل معيار إمّا **مُثبَت** (له فحص منفَّذ الآن) أو **غير مُثبَت بعد**
(مع سبب النقص). لا معيار يُعدّ «مُثبَت» بلا فحص يعمل فعلاً.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Criterion:
    """معيار قبول واحد."""

    id: str
    title_ar: str
    artefact: str
    proof_key: str | None
    not_proven_reason_ar: str = ""
    proof_kind_ar: str = "بشواهد حيّة تُنفَّذ في كل تشغيل"

    @property
    def implemented(self) -> bool:
        return self.proof_key is not None


CRITERIA: tuple[Criterion, ...] = (
    Criterion(
        "AC-01",
        "استقبال فكرة",
        "cli/run_request.json",
        "cli_run_creates_project",
    ),
    Criterion(
        "AC-02",
        "تحويل الفكرة إلى متطلبات",
        "artifacts/prd.md, user_stories.json",
        "idea_produces_prd",
        proof_kind_ar="بشواهد آلية — البيانات الحيّة معلّقة (تحتاج DEEPSEEK_API_KEY)",
    ),
    Criterion(
        "AC-03",
        "تحليل منافسين",
        "artifacts/market/competitor_matrix.csv",
        "research_produces_competitors",
        proof_kind_ar="بشواهد آلية — البيانات الحيّة معلّقة (تحتاج DEEPSEEK_API_KEY)",
    ),
    Criterion(
        "AC-04",
        "البحث عن مكونات",
        "artifacts/research/candidates.jsonl",
        "research_produces_candidates",
        proof_kind_ar="بشواهد آلية — البيانات الحيّة معلّقة (تحتاج DEEPSEEK_API_KEY)",
    ),
    Criterion(
        "AC-05",
        "تقييم التراخيص والتبعيات",
        "artifacts/research/scans/",
        "licenses_decided",
        "التبعية في هذا المستودع مسجَّلة؛ بحث المكوّنات الخارجية (§29) منفصل.",
    ),
    Criterion(
        "AC-06",
        "تسجيل قرارات إعادة الاستخدام",
        "artifacts/decisions/decision_log.jsonl",
        "reuse_decisions_recorded",
    ),
    Criterion(
        "AC-07",
        "AppIR قابل للتحقق",
        "appir/appir.json + validate_report.json",
        "ir_rules_reject_negatives",
    ),
    Criterion(
        "AC-08",
        "إنشاء مشروع من قالب",
        "workspace/ + build logs",
        "scaffold_creates_structure",
    ),
    Criterion(
        "AC-09",
        "دمج مكونات",
        "provenance.jsonl",
        "every_import_has_record",
    ),
    Criterion(
        "AC-10",
        "بناء بلا أخطاء حرجة",
        "reports/build.json",
        "gates_pass",
    ),
    Criterion(
        "AC-11",
        "تشغيل الاختبارات وتسجيل النتائج",
        "reports/tests.json",
        "tests_report_has_results",
    ),
    Criterion(
        "AC-12",
        "اكتشاف الأخطاء وإصلاحها",
        "reports/repair.json",
        "injected_defect_is_detected",
    ),
    Criterion(
        "AC-13",
        "إيقاف العمليات الخطرة",
        "reports/escalation.json",
        "zero_budget_stops",
    ),
    Criterion(
        "AC-14",
        "فحص مستقل",
        "reports/inspector_report.md",
        "injected_defect_is_detected",
    ),
    Criterion(
        "AC-15",
        "تقارير جودة وأمان وتراخيص",
        "reports/{quality,security,license}.md",
        "reports_exist_and_non_empty",
    ),
    Criterion(
        "AC-16",
        "حفظ الحالة والاستئناف",
        "state.json + run_events",
        "resume_after_crash",
    ),
    Criterion(
        "AC-17",
        "إدارة الميزانية",
        "reports/costs.json",
        "budget_overrun_is_blocked",
    ),
    Criterion(
        "AC-18",
        "تسليم الملفات والتوثيق",
        "docs/ + artifacts/",
        "required_files_present",
    ),
    Criterion(
        "AC-19",
        "إعادة البناء من الإصدارات",
        "provenance + lockfiles",
        "rebuild_hash_is_stable",
    ),
    Criterion(
        "AC-20",
        "إضافة محركات دون إعادة بناء",
        "examples/plugin_minimal/",
        "plugin_works_without_core_change",
    ),
)

CRITERIA_BY_ID: dict[str, Criterion] = {criterion.id: criterion for criterion in CRITERIA}


def implemented_criteria() -> tuple[Criterion, ...]:
    """المعايير التي لها فحص منفَّذ."""
    return tuple(criterion for criterion in CRITERIA if criterion.implemented)


def pending_criteria() -> tuple[Criterion, ...]:
    """المعايير غير المُثبَتة بعد، مع سبب النقص."""
    return tuple(criterion for criterion in CRITERIA if not criterion.implemented)
