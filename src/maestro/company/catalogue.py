"""كتالوج الشركة: ثمانية نطاقات، أربع وعشرون قدرة، وبوابة واحدة تُستدعى أربعاً.

هذا الملف هو **مصدر الحقيقة الوحيد** لما تستطيع الشركة فعله. كل ما عداه
— السجل، البوابات، الموجّه، التوثيق — يُشتقّ منه أو يُفحص مقابله.

قاعدة الكتالوج: **قدرة واحدة = وكيل واحد = عقد واحد**. والقدرات التي تختلف
بصفة «تملك ذاكرة خاصة» لا تُضاف كقدرة جديدة، بل كـ**استدعاء إضافي** لقدرة
موجودة — ولهذا تُكتب البوابات الأربع بوابة واحدة تُستدعى في أربعة مواضع.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Domain:
    """نطاق واحد داخل الشركة: له مدير واحد ومهمة مكتوبة."""

    key: str
    name_ar: str
    mission_ar: str
    director_agent: str


@dataclass(frozen=True)
class Capability:
    """قدرة واحدة: وكيل واحد، ميزانية واحدة، سجل أدلة واحد."""

    name: str
    domain: str
    name_ar: str
    agent: str
    tools: tuple[str, ...] = ()
    authority: int = 1
    critical: bool = False
    ensemble: tuple[str, ...] = ("local", "api", "fallback")
    min_agreement: int = 1
    fallback_condition_ar: str = "فشل النموذج أو خروجه بمخرج فارغ"
    gates: tuple[str, ...] = ()
    specializations: tuple[str, ...] = ()

    @property
    def is_gated(self) -> bool:
        """هل يمرّ ببوابة قبل تنفيذه؟"""
        return bool(self.gates)


#: النطاقات الثمانية. لكل نطاق مدير واحد — لا نطاقات بلا مالك.
DOMAINS: tuple[Domain, ...] = (
    Domain(
        key="commercial",
        name_ar="التجاري",
        mission_ar="من الفكرة إلى النموذج المالي والتسعير المبرَّر",
        director_agent="commercial_director",
    ),
    Domain(
        key="community",
        name_ar="المجتمع",
        mission_ar="اختبار المجتمع: لوحة شرائح تُستدعى في أربعة مواضع من الطريق",
        director_agent="community_director",
    ),
    Domain(
        key="research",
        name_ar="البحث والاختيار",
        mission_ar="ترشيح المشاريع وتقييمها واختيار واحد",
        director_agent="research_director",
    ),
    Domain(
        key="engineering",
        name_ar="الهندسة",
        mission_ar="مراجعة الكود ودمجه واختباره وواجهات الدفع",
        director_agent="engineering_director",
    ),
    Domain(
        key="experience",
        name_ar="التجربة",
        mission_ar="التصميم وبناء الواجهة ومراجعتها",
        director_agent="experience_director",
    ),
    Domain(
        key="quality",
        name_ar="الجودة",
        mission_ar="فحص أمني وضغط وامتثال",
        director_agent="quality_director",
    ),
    Domain(
        key="release",
        name_ar="الإصدار",
        mission_ar="فحص الإصدار وتوقيعه ونشره ومراقبته",
        director_agent="release_director",
    ),
    Domain(
        key="data",
        name_ar="البيانات والقوالب",
        mission_ar="خطوط بيانات المنتج وقوالب التطبيقات الثلاث",
        director_agent="data_director",
    ),
)

#: البوابة الواحدة: قدرة واحدة، تُستدعى في أربعة مواضع.
COMMUNITY_GATE = "community.community_test"

#: مواضع الاستدعاء الأربعة لبوابة المجتمع.
GATE_INVOCATIONS: tuple[str, ...] = (
    "commercial.idea_framing",
    "experience.ui_build",
    "commercial.pricing",
    "engineering.payment_interface",
)


def _capability(
    name: str,
    domain: str,
    name_ar: str,
    agent: str,
    *,
    tools: tuple[str, ...] = (),
    authority: int = 1,
    critical: bool = False,
    min_agreement: int = 1,
    fallback_condition_ar: str = "فشل النموذج أو خروجه بمخرج فارغ",
    gates: tuple[str, ...] = (),
    specializations: tuple[str, ...] = (),
    ensemble: tuple[str, ...] = ("local", "api", "fallback"),
) -> Capability:
    return Capability(
        name=name,
        domain=domain,
        name_ar=name_ar,
        agent=agent,
        tools=tools,
        authority=authority,
        critical=critical,
        ensemble=ensemble,
        min_agreement=min_agreement,
        fallback_condition_ar=fallback_condition_ar,
        gates=gates,
        specializations=specializations,
    )


#: القدرات الأربع والعشرون.
CAPABILITIES: tuple[Capability, ...] = (
    # ── التجاري (4) ────────────────────────────────────────────────────────
    _capability(
        "commercial.idea_framing",
        "commercial",
        "صياغة الفكرة وعرضها على لوحة المجتمع",
        "idea_framer",
        tools=("model.generate",),
        gates=(COMMUNITY_GATE,),
        fallback_condition_ar="تشابه الفكرة مع فكرة أخرى أو خروج بلا بنية",
    ),
    _capability(
        "commercial.market_research",
        "commercial",
        "بحث السوق والمنافسين",
        "market_researcher",
        tools=("http.get", "vector.search"),
        fallback_condition_ar="تعذّر الوصول إلى المصدر أو ردّ بلا أدلة",
    ),
    _capability(
        "commercial.business_model",
        "commercial",
        "نموذج العمل ومسار الإيراد",
        "model_builder",
        tools=("model.generate", "vector.search"),
        authority=2,
    ),
    _capability(
        "commercial.pricing",
        "commercial",
        "التسعير المبرَّر برقم",
        "pricer",
        tools=("model.generate", "vector.search"),
        authority=2,
        critical=True,
        min_agreement=2,
        gates=(COMMUNITY_GATE, "quality.compliance_review"),
        fallback_condition_ar="تباين رقمي فوق 10% بين نموذجين",
        ensemble=("api", "local", "fallback"),
    ),
    # ── المجتمع (1 تُستدعى 4 مرات) ────────────────────────────────────────
    _capability(
        COMMUNITY_GATE,
        "community",
        "اختبار المجتمع — بوابة واحدة بأربعة استدعاءات",
        "community_tester",
        tools=("model.generate", "http.get"),
        authority=2,
        critical=True,
        min_agreement=2,
        fallback_condition_ar="انخفاض قبول اللوحة تحت الحدّ أو تعذّر تشغيل اللوحة",
        ensemble=("api", "fallback", "local"),
    ),
    # ── البحث والاختيار (3) ───────────────────────────────────────────────
    _capability(
        "research.project_research",
        "research",
        "بحث المشروع ومصدره ورخصته",
        "project_researcher",
        tools=("http.get", "git.read", "vector.search"),
        fallback_condition_ar="فشل التحقق من الترخيص أو المصدر",
    ),
    _capability(
        "research.project_evaluation",
        "research",
        "تقييم المشروع بمعيار معلن",
        "project_evaluator",
        tools=("vector.search", "model.generate"),
    ),
    _capability(
        "research.project_selection",
        "research",
        "اختيار مشروع واحد وبتعليل مكتوب",
        "project_selector",
        tools=("model.generate",),
        authority=2,
        gates=("research.project_evaluation",),
    ),
    # ── الهندسة (4) ───────────────────────────────────────────────────────
    _capability(
        "engineering.code_review",
        "engineering",
        "مراجعة الكود وفحص الثغرات",
        "code_reviewer",
        tools=("git.read", "model.generate"),
        critical=True,
        min_agreement=2,
        fallback_condition_ar="ثقة أقل من 0.7 أو خطأ أداة",
        ensemble=("local", "api", "fallback"),
    ),
    _capability(
        "engineering.code_merge",
        "engineering",
        "الدمج بعد اجتياز المراجعة والاختبار",
        "code_merger",
        tools=("git.read", "model.generate"),
        gates=("engineering.code_review", "engineering.code_test"),
    ),
    _capability(
        "engineering.code_test",
        "engineering",
        "كتابة الاختبارات وتشغيلها",
        "test_engineer",
        tools=("git.read", "model.generate"),
    ),
    _capability(
        "engineering.payment_interface",
        "engineering",
        "واجهة الدفع والعقود",
        "payment_engineer",
        tools=("model.generate", "http.post"),
        authority=3,
        critical=True,
        min_agreement=2,
        gates=(COMMUNITY_GATE, "quality.data_security"),
        fallback_condition_ar="رفض المزوّد أو ردّ بلا توقيع",
    ),
    # ── التجربة (3) ───────────────────────────────────────────────────────
    _capability(
        "experience.ui_design",
        "experience",
        "تصميم الواجهة والأيقونات",
        "ui_designer",
        tools=("model.generate", "render.image"),
    ),
    _capability(
        "experience.ui_build",
        "experience",
        "بناء الواجهة",
        "ui_builder",
        tools=("model.generate", "git.read"),
        gates=(COMMUNITY_GATE, "experience.ui_review"),
    ),
    _capability(
        "experience.ui_review",
        "experience",
        "مراجعة الواجهة وقبولها",
        "ui_reviewer",
        tools=("model.generate", "render.image"),
    ),
    # ── الجودة (4) ────────────────────────────────────────────────────────
    _capability(
        "quality.data_security",
        "quality",
        "فحص أمن البيانات والصلاحيات",
        "security_inspector",
        tools=("git.read", "model.generate"),
        critical=True,
        min_agreement=2,
        fallback_condition_ar="نتيجة غير حاسمة",
        ensemble=("local", "api", "fallback"),
    ),
    _capability(
        "quality.penetration_test",
        "quality",
        "اختبار الاختراق",
        "penetration_tester",
        tools=("http.get", "model.generate"),
        authority=2,
    ),
    _capability(
        "quality.load_test",
        "quality",
        "اختبار الحمل والضغط",
        "load_tester",
        tools=("http.get", "model.generate"),
        fallback_condition_ar="تجاوز حدّ المدة أو فشل نقطةHealth",
    ),
    _capability(
        "quality.compliance_review",
        "quality",
        "مراجعة الامتثال وسياسات المنصة",
        "compliance_reviewer",
        tools=("model.generate", "vector.search"),
        authority=2,
    ),
    # ── الإصدار (3) ───────────────────────────────────────────────────────
    _capability(
        "release.release_qa",
        "release",
        "فحص الإصدار النهائي",
        "release_inspector",
        tools=("git.read", "model.generate"),
        gates=("engineering.code_test", "quality.load_test"),
    ),
    _capability(
        "release.release_signing",
        "release",
        "توقيع حزمة الإصدار",
        "release_signer",
        tools=("model.generate",),
        authority=3,
        gates=("release.release_qa",),
    ),
    _capability(
        "release.release_publish",
        "release",
        "النشر والمراقبة",
        "release_publisher",
        tools=("http.post", "model.generate"),
        authority=3,
        critical=True,
        min_agreement=2,
        gates=("release.release_signing", "quality.data_security"),
        fallback_condition_ar="فشل النشر أو فشل فحص الصحة بعد النشر",
    ),
    # ── البيانات والقوالب (2) ─────────────────────────────────────────────
    _capability(
        "data.data_pipeline",
        "data",
        "خط بيانات المنتج: من ملف المورّد إلى منشور",
        "data_pipeline",
        tools=("model.generate", "saleor.graphql", "fs.write"),
        authority=2,
        critical=True,
        min_agreement=2,
        gates=("quality.compliance_review",),
        specializations=("catalog.ingest",),
        fallback_condition_ar="خلل في عقد الردّ أو في شكل المدخل",
    ),
    _capability(
        "data.app_template",
        "data",
        "قوالب web وandroid وios",
        "template_builder",
        tools=("git.read", "model.generate"),
        gates=("research.project_selection",),
    ),
)


def capabilities() -> tuple[Capability, ...]:
    """كل القدرات."""
    return CAPABILITIES


def domains() -> tuple[Domain, ...]:
    """كل النطاقات."""
    return DOMAINS


def by_domain() -> dict[str, tuple[Capability, ...]]:
    """القدرات مجمّعةً بنطاقها."""
    grouped: dict[str, list[Capability]] = {domain.key: [] for domain in DOMAINS}
    for capability in CAPABILITIES:
        grouped.setdefault(capability.domain, []).append(capability)
    return {key: tuple(values) for key, values in grouped.items()}


def critical_capabilities() -> tuple[Capability, ...]:
    """القدرات الحرجة: لا تُقبل بنموذج واحد."""
    return tuple(capability for capability in CAPABILITIES if capability.critical)


def gated_capabilities() -> tuple[Capability, ...]:
    """القدرات التي تمرّ ببوابة قبل تنفيذها."""
    return tuple(capability for capability in CAPABILITIES if capability.is_gated)


def specialization_targets() -> dict[str, str]:
    """خريطة التخصّصات: اسم التخصّص ← القدرة الأم."""
    targets: dict[str, str] = {}
    for capability in CAPABILITIES:
        for specialization in capability.specializations:
            targets[specialization] = capability.name
    return targets


def capability_by_name(name: str) -> Capability | None:
    """قدرة باسمها، أو None."""
    for capability in CAPABILITIES:
        if capability.name == name:
            return capability
    return None
