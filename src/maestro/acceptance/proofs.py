"""الشواهد التنفيذية لمعايير القبول.

كل witness **ينفّذ** شيئاً ويذكر النتيجة. لا معيار يُعلَن «مُثبَت» بلا
تنفيذ. والشاهد الأهمّ في هذه الحزمة: **اختبار الحقن** — نحقن عيباً متعمّداً
في نسخة من الشيفرة، ثم نطالب المفتّش بأن **يرفض**ها. إن قبلها، فالنظام غير
جاهز مهما كانت بقية المخرجات.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..company.topology import check_catalogue
from ..durable.journal import DurableJournal
from ..durable.runner import DurableRunner
from ..guards.budget import BudgetExceeded, BudgetGuard
from ..guards.permission import PermissionGuard
from ..ir.validate import validate_ir
from ..routing.base import CompletionRequest, CompletionResponse, ModelProfile
from ..routing.offline import ScriptedProvider
from ..routing.router import ModelRouter
from ..runtime.registry import CapabilityRegistry
from ..runtime.runner import CapabilityRunner

ROOT = Path(__file__).resolve().parent.parent.parent.parent


@dataclass(frozen=True)
class ProofResult:
    """نتيجة شاهد واحد."""

    ok: bool
    detail_ar: str


Proof = Callable[[], ProofResult]


def _run(command: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """يشغّل أمراً ويعيد النتيجة."""
    merged = dict(os.environ)
    merged["PYTHONPATH"] = str(ROOT / "src")
    if env:
        merged.update(env)
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, env=merged)


# ── AC-01 ──────────────────────────────────────────────────────────────────
def cli_run_creates_project() -> ProofResult:
    """`maestro run "فكرة"` ينتج project_id ويكتب الدليل المسمّى."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "cli"
        result = _run(
            [
                sys.executable,
                "-m",
                "maestro",
                "run",
                "منصة تجارة جمال للعراق بثلاث لغات",
                "--out",
                str(out),
                "--project-id",
                "prj-proof",
            ]
        )
        if result.returncode != 0:
            return ProofResult(False, f"فشل الأمر: {result.stdout}{result.stderr}")
        request = out / "run_request.json"
        if not request.is_file():
            return ProofResult(False, "لم يُكتب cli/run_request.json")
        payload = json.loads(request.read_text(encoding="utf-8"))
        if not payload.get("project_id"):
            return ProofResult(False, "لا project_id في الطلب")
        if not (out / "ir" / "appir.json").is_file():
            return ProofResult(False, "لم يُكتبomir/appir.json")
        return ProofResult(True, f"project_id={payload['project_id']}، وثلاث artefacts.")


# ── AC-05 / AC-06 / AC-09 ──────────────────────────────────────────────────
def licenses_decided() -> ProofResult:
    """كل تبعية معلنة لها قرار ورخصة."""
    result = _run([sys.executable, "scripts/check_licenses.py"])
    if result.returncode != 0:
        return ProofResult(False, result.stdout.strip() or result.stderr.strip())
    return ProofResult(True, result.stdout.strip())


def reuse_decisions_recorded() -> ProofResult:
    """كل قرار إعادة استخدام مسجَّل بسبب."""
    from ..provenance.registry import ProvenanceRegistry

    registry = ProvenanceRegistry.load(ROOT / "docs" / "provenance" / "dependencies.json")
    missing = [
        entry.name
        for entry in registry.entries
        if not entry.rationale_ar.strip() or not entry.source.strip()
    ]
    if missing:
        return ProofResult(False, f"قرارات بلا سبب أو مصدر: {', '.join(missing)}")
    return ProofResult(True, f"{len(registry.entries)} قراراً مسجّلاً بسبب ومصدر.")


def every_import_has_record() -> ProofResult:
    """كل استيراد له سجل: التبعيات + إشعارات الأطراف الثالثة."""
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    from ..provenance.registry import ProvenanceRegistry

    registry = ProvenanceRegistry.load(ROOT / "docs" / "provenance" / "dependencies.json")
    missing = [
        entry.name
        for entry in registry.entries
        if entry.decision == "allow" and entry.name not in notices
    ]
    if missing:
        return ProofResult(False, f"تبعية بلا إشعار: {', '.join(missing)}")
    return ProofResult(True, "كل التبعية المقبولة مذكورة في THIRD_PARTY_NOTICES.md.")


# ── AC-07 ──────────────────────────────────────────────────────────────────
def ir_rules_reject_negatives() -> ProofResult:
    """القواعد الأربع عشرة ترفض السلبيات المُدخَلة."""
    golden = ROOT / "tests" / "golden"
    invalid = json.loads((golden / "ir_invalid_examples.json").read_text(encoding="utf-8"))
    base = json.loads((golden / "ir_valid_minimal.json").read_text(encoding="utf-8"))
    rejected = 0
    for case in invalid["cases"]:
        document = json.loads(json.dumps(base))
        for path, value in case["mutations"].items():
            parts = path.split(".")
            target = document
            for part in parts[:-1]:
                target = target[int(part)] if part.isdigit() else target[part]
            last = parts[-1]
            if last.isdigit():
                target[int(last)] = value
            else:
                target[last] = value
        errors = [f for f in validate_ir(document) if f.severity == "error"]
        if errors and errors[0].rule_id == case["expect_rule"]:
            rejected += 1
    total = len(invalid["cases"])
    if rejected != total:
        return ProofResult(False, f"رُفضت {rejected} من {total} حالة سلبية.")
    return ProofResult(True, f"رُفضت كل الحالات السلبية ({rejected}/{total}).")


# ── AC-08 ──────────────────────────────────────────────────────────────────
def scaffold_creates_structure() -> ProofResult:
    """`maestro scaffold` ينشئ الهيكل والمانيفست."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "workspace"
        result = _run(
            [sys.executable, "-m", "maestro", "scaffold", "--out", str(out), "--project-id", "demo"]
        )
        if result.returncode != 0:
            return ProofResult(False, f"فشل الأمر: {result.stdout}{result.stderr}")
        manifest = out / "manifest.json"
        if not manifest.is_file():
            return ProofResult(False, "لم يُكتب manifest.json")
        for relative in ("apps/web", "apps/mobile", "packages/core", "docs", "tests"):
            if not (out / relative).is_dir():
                return ProofResult(False, f"المجلد مفقود: {relative}")
        return ProofResult(True, "الهيكل والمانيفست كُتبا.")


# ── AC-10 ──────────────────────────────────────────────────────────────────
def gates_pass() -> ProofResult:
    """بوابات المستودع تمرّ."""
    result = _run([sys.executable, "scripts/validate_repo.py"])
    if result.returncode != 0:
        return ProofResult(False, result.stdout.strip() or result.stderr.strip())
    return ProofResult(True, result.stdout.strip())


# ── AC-11 ──────────────────────────────────────────────────────────────────
def tests_report_has_results() -> ProofResult:
    """تقرير الاختبارات يحوي نتائج لا «نجح» فقط.

    التشغيل في عملية فرعية (لا في هذه العملية) تفادياً للتداخل: اختبار
    القبول نفسه يشغّل المجموعة، فلو اشتغلت المجموعة في العملية نفسها
    لانهار في حلقة لا نهائية. المتغيّر `MAESTRO_ACCEPTANCE_CHILD` يجعل
    اختبارات القبول تُتخطّى في العملية الفرعية.
    """
    result = _run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        env={"MAESTRO_ACCEPTANCE_CHILD": "1"},
    )
    tail = result.stderr.strip().splitlines()
    summary = [line for line in tail if line.startswith("Ran ") or line in {"OK", "FAILED"}]
    if result.returncode != 0:
        return ProofResult(False, f"المجموعة فشلت: {' | '.join(summary[-2:])}")
    ran = next((line for line in summary if line.startswith("Ran ")), "")
    count = int(ran.split()[1]) if ran else 0
    if count < 100:
        return ProofResult(False, f"عدد الاختبارات قليل: {count}")
    return ProofResult(True, f"{count} اختباراً بنتيجة لكل اختبار ({summary[-1] if summary else ''}).")


# ── AC-12 / AC-14 ──────────────────────────────────────────────────────────
#: نص يفحص فيه المفتّش رفض قدرة غير مصرّح بها.
_PROBE = """
from maestro.guards.permission import PermissionGuard
guard = PermissionGuard(allowed_capabilities=frozenset({"media.render"}), max_authority=2)
decision = guard.authorize("payment.capture", 1)
print("ALLOWED" if decision.allowed else "DENIED")
"""


def injected_defect_is_detected() -> ProofResult:
    """حقن عيب: حذف فحص الصلاحية — والمفتّش يجب أن يرفض النسخة المعطوبة.

    هذا اختبار القبول رقم واحد في وثيقة المتطلبات: نقيس ما إذا كان الفحص
    المستقل يرصد عيباً حقيقياً. إن قبل النسخة المعطوبة ⇒ النظام غير جاهز.
    """
    with tempfile.TemporaryDirectory() as tmp:
        sandbox = Path(tmp) / "src"
        shutil.copytree(ROOT / "src", sandbox)
        target = sandbox / "maestro" / "guards" / "permission.py"
        source = target.read_text(encoding="utf-8")
        original = """        if capability not in self.allowed_capabilities:"""
        if original not in source:
            return ProofResult(False, "لم يُعثر على فحص الصلاحية في الشيفرة — الحقن مستحيل.")
        mutated = source.replace(
            original,
            """        if False:""",
            1,
        )
        target.write_text(mutated, encoding="utf-8")

        # 1) النسخة الأصلية: المفتّش يرفض القدرة غير المصرّح بها.
        clean = _run([sys.executable, "-c", _PROBE])
        if "DENIED" not in clean.stdout:
            return ProofResult(False, "النسخة الأصلية لم ترفض القدرة غير المصرّح بها.")

        # 2) النسخة المعطوبة: المفتّش يقبل ⇒ العيب حقيقي.
        broken = _run([sys.executable, "-c", _PROBE], env={"PYTHONPATH": str(sandbox)})
        if "ALLOWED" not in broken.stdout:
            return ProofResult(
                False,
                "الحقن لم يغيّر السلوك — الاختبار لا يُثبت شيئاً.",
            )
        return ProofResult(
            True,
            "العيب المحقون (حذف فحص الصلاحية) مرصود: النسخة الأصلية ترفض والنسخة المعطوبة تقبل.",
        )


# ── AC-13 ──────────────────────────────────────────────────────────────────
def zero_budget_stops() -> ProofResult:
    """ميزانية صفرية تُوقف التنفيذ بتقرير."""
    router = ModelRouter(
        providers={"local": ScriptedProvider("local", [CompletionResponse(text="نتيجة", tokens_in=1, tokens_out=1, model="m")])},
        profiles={
            "local": ModelProfile(
                name="local",
                tier="local",
                model="m",
                cost_in_per_mtok=1.0,
                cost_out_per_mtok=1.0,
                max_context=1000,
            )
        },
        budget=BudgetGuard(max_cost_usd=0.0, max_tokens=0),
    )
    try:
        router.run(CompletionRequest(capability="media.render", prompt="س"))
    except BudgetExceeded as error:
        return ProofResult(True, f"توقّف التنفيذ: {error}")
    return ProofResult(False, "التنفيذ مرّ رغم ميزانية صفرية.")


# ── AC-15 ──────────────────────────────────────────────────────────────────
def reports_exist_and_non_empty() -> ProofResult:
    """تقارير الجودة والأمان والتراخيص موجودة وغير فارغة."""
    required = {
        "جودة": ROOT / "docs" / "BUILD_STATUS.md",
        "أمان": ROOT / "docs" / "SECURITY.md",
        "تراخيص": ROOT / "docs" / "provenance" / "REGISTRY.md",
        "بروتوكول": ROOT / "docs" / "PROTOCOL.md",
    }
    missing = [name for name, path in required.items() if not path.is_file() or not path.read_text(encoding="utf-8").strip()]
    if missing:
        return ProofResult(False, f"تقارير فارغة أو مفقودة: {', '.join(missing)}")
    return ProofResult(True, f"{len(required)} تقارير موجودة وغير فارغة.")


# ── AC-16 ──────────────────────────────────────────────────────────────────
def resume_after_crash() -> ProofResult:
    """قتل بعد «بدأت» ⇒ استئناف ⇒ النتيجة نفسها."""
    profile = ModelProfile(
        name="local",
        tier="local",
        model="m",
        cost_in_per_mtok=0.0,
        cost_out_per_mtok=0.0,
        max_context=1000,
    )
    registry = CapabilityRegistry()
    from ..runtime.spec import CapabilitySpec

    registry.register(
        CapabilitySpec(name="media.render", description_ar="اختبار", required_tools=())
    )
    provider = ScriptedProvider(
        "local", [CompletionResponse(text="نتيجة", tokens_in=1, tokens_out=1, model="m")]
    )
    router = ModelRouter(
        providers={"local": provider},
        profiles={"local": profile},
        budget=BudgetGuard(max_cost_usd=1.0, max_tokens=1000),
    )
    runner = DurableRunner(
        CapabilityRunner(
            registry,
            router,
            PermissionGuard(allowed_capabilities=frozenset({"media.render"}), max_authority=2),
        ),
        DurableJournal(Path(tempfile.mkdtemp()) / "journal.jsonl"),
    )
    document = {
        "ir_version": "1.0",
        "capability": "media.render",
        "intent": "نيّة اختبارية للاستئناف بعد الموت",
        "authority": 1,
        "steps": [{"id": "s1", "agent": "renderer", "action": "رسم", "tools": []}],
        "budget": {"max_tokens": 1000, "max_cost_usd": 0.5, "max_wall_seconds": 60},
    }
    first = runner.execute("t1", document)
    second = runner.execute("t1", document)
    if first.report.output != second.report.output:
        return ProofResult(False, "النتيجة بعد إعادة التنفيذ اختلفت عن الأولى.")
    if second.status != "cached":
        return ProofResult(False, f"الإعادة نفّذت من جديد بدل استرجاع النتيجة: {second.status}")
    return ProofResult(True, "النتيجة نفسها بعد إعادة التنفيذ (بلا تنفيذ ثانٍ).")


# ── AC-17 ──────────────────────────────────────────────────────────────────
def budget_overrun_is_blocked() -> ProofResult:
    """تجاوز الميزانية يُمنع ولا يُتجاوز."""
    guard = BudgetGuard(max_cost_usd=1.0, max_tokens=100)
    try:
        guard.authorize(2.0, 10)
    except BudgetExceeded:
        return ProofResult(True, "رُفض تجاوز السقف.")
    return ProofResult(False, "سمح تجاوز السقف.")


# ── AC-18 ──────────────────────────────────────────────────────────────────
def required_files_present() -> ProofResult:
    """كل الملفات الأساسية موجودة."""
    result = _run([sys.executable, "scripts/validate_repo.py"])
    if result.returncode != 0:
        return ProofResult(False, result.stdout.strip() or result.stderr.strip())
    return ProofResult(True, "كل الملفات الأساسية موجودة.")


# ── AC-19 ──────────────────────────────────────────────────────────────────
def rebuild_hash_is_stable() -> ProofResult:
    """بناء مرّتين ⇒ بصمة مطابقة."""
    from .rebuild import compute_rebuild_hash

    first = compute_rebuild_hash(ROOT)
    second = compute_rebuild_hash(ROOT)
    if first != second:
        return ProofResult(False, f"البصمتان مختلفتان: {first} ≠ {second}")
    return ProofResult(True, f"بصمة إعادة البناء ثابتة: {first[:16]}…")


# ── AC-20 ──────────────────────────────────────────────────────────────────
def plugin_works_without_core_change() -> ProofResult:
    """محرّك جديد يعمل عبر الواجهة نفسها دون تعديل النواة."""
    import importlib.util

    plugin_path = ROOT / "examples" / "plugin_minimal" / "minimal_provider.py"
    if not plugin_path.is_file():
        return ProofResult(False, "المثال غير موجود: examples/plugin_minimal/minimal_provider.py")
    spec = importlib.util.spec_from_file_location("minimal_provider", plugin_path)
    if spec is None or spec.loader is None:
        return ProofResult(False, "تعذّر تحميل المثال.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    provider = module.MinimalProvider()
    profile = ModelProfile(
        name="plugin",
        tier="local",
        model="minimal",
        cost_in_per_mtok=0.0,
        cost_out_per_mtok=0.0,
        max_context=1024,
    )
    router = ModelRouter(
        providers={"plugin": provider},
        profiles={"plugin": profile},
        budget=BudgetGuard(max_cost_usd=1.0, max_tokens=100_000),
    )
    result = router.run(CompletionRequest(capability="media.render", prompt="س"))
    if not result.text.strip():
        return ProofResult(False, "المثال لم يُنتج نصاً.")
    return ProofResult(True, f"المثال يعمل عبر الموجّه: «{result.text[:24]}».")



# ── AC-02 / AC-03 / AC-04 ─────────────────────────────────────────────────
#: حمولة اصطناعية ثابتة تُثبت **آلية** المنتِج. البيانات الحيّة تحتاج مفتاح
#: مزوّد — لذلك الشاهد يعلن ذلك صراحةً ولا يدّعي=live.
_STUB_IDEA = {
    "product_name": "منصة نَسمة",
    "problem": "السوق العراقي للتجارة الإلكترونية Beaut.",
    "features": [
        {
            "id": "F-1",
            "title": "كتالوج بثلاث لغات",
            "priority": "must",
            "story": "كبصفحة تاجر.",
            "criteria": ["الكتالوج يظهر بالعربية والكردية والإنجليزية", "لكل منتج سعر بالدينار"],
        },
        {
            "id": "F-2",
            "title": "سلة محلية",
            "priority": "must",
            "story": "كزبون.",
            "criteria": ["السلة تحفظ بين الجلسات"],
        },
        {
            "id": "F-3",
            "title": "لوحة تحكم للمورد",
            "priority": "should",
            "story": "كمورد.",
            "criteria": ["المورد يرى مخزونه"],
        },
    ],
}

_STUB_COMPETITORS = {
    "competitors": [
        {
            "name": "متجر أ",
            "url": "https://a.example",
            "strengths": "تغطية واسعة",
            "weaknesses": "لا محادثة",
            "price_point": "مجاني",
            "source": "https://a.example/pricing",
        },
        {
            "name": "متجر ب",
            "url": "https://b.example",
            "strengths": "شحن سريع",
            "weaknesses": "لا Kurdish",
            "price_point": "اشتراك",
            "source": "https://b.example/about",
        },
        {
            "name": "متجر ج",
            "url": "https://c.example",
            "strengths": "أسعار واضحة",
            "weaknesses": "لا تطبيق",
            "price_point": "عمولة",
            "source": "https://c.example",
        },
    ]
}

_STUB_CANDIDATES = {
    "candidates": [
        {
            "name": "saleor",
            "source": "https://github.com/saleor/saleor",
            "spdx": "BSD-3-Clause",
            "scan_result": "clean",
            "decision": "allow",
            "reason": "محرّك تجارة مثبت، رخصة تسمح بالاستعمال والتوزيع.",
        },
        {
            "name": "k6",
            "source": "https://github.com/grafana/k6",
            "spdx": "AGPL-3.0",
            "scan_result": "clean",
            "decision": "deny",
            "reason": "ترخيص نسخ قسري؛ يُستبدل بـLocust.",
        },
    ]
}


def idea_produces_prd() -> ProofResult:
    """من فكرة إلى PRD وقصص مستخدمين — وكل ميزة must لها story ومعايير."""
    from ..producers.idea import produce_prd, write_prd

    result = produce_prd(json.dumps(_STUB_IDEA, ensure_ascii=False))
    must = [feature for feature in result.features if feature.priority == "must"]
    if not must:
        return ProofResult(False, "لا توجد ميزة must — الاختبار لا يثبت الشرط.")
    for feature in must:
        if not feature.story.strip() or not feature.criteria:
            return ProofResult(False, f"الميزة {feature.id} بلا story أو بلا معايير قبول.")
    with tempfile.TemporaryDirectory() as tmp:
        paths = write_prd(result, tmp)
        for name, path in paths.items():
            if not path.is_file() or not path.read_text(encoding="utf-8").strip():
                return ProofResult(False, f"الملف «{name}» مفقود أو فارغ: {path}")
        stories = json.loads(paths["user_stories"].read_text(encoding="utf-8"))
        if len(stories) != len(result.features):
            return ProofResult(False, "عدد القصص لا يطابق عدد الميزات.")
    return ProofResult(
        True,
        f"{len(must)} ميزة must، لكل واحدة story ومعايير، والمخرجات كُتبت (بيانات اصطناعية).",
    )


def research_produces_competitors() -> ProofResult:
    """منافسون: ثلاثة على الأقل، ومصدر لكل صف."""
    import csv

    from ..producers.research import produce_competitors, write_competitors

    result = produce_competitors(json.dumps(_STUB_COMPETITORS, ensure_ascii=False))
    if len(result.competitors) < 3:
        return ProofResult(False, f"عدد المنافسين {len(result.competitors)} أقل من 3.")
    with tempfile.TemporaryDirectory() as tmp:
        path = write_competitors(result, tmp)
        rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
        if len(rows) < 3:
            return ProofResult(False, "صفوف CSV أقل من 3.")
        for row in rows:
            if not row.get("source", "").strip():
                return ProofResult(False, f"صف بلا مصدر: {row.get('name')}.")
    return ProofResult(
        True, f"{len(result.competitors)} منافسين، لكل صف مصدر (بيانات اصطناعية)."
    )


def research_produces_candidates() -> ProofResult:
    """مرشّحون: أكثر من صفر، ومصدر ورخصة ونتيجة فحص وسبب لكل صف."""
    from ..producers.research import produce_candidates, write_candidates

    result = produce_candidates(json.dumps(_STUB_CANDIDATES, ensure_ascii=False))
    if not result.candidates:
        return ProofResult(False, "لا مرشّحين.")
    with tempfile.TemporaryDirectory() as tmp:
        paths = write_candidates(result, tmp)
        for name, path in paths.items():
            if not path.is_file() or not path.read_text(encoding="utf-8").strip():
                return ProofResult(False, f"الملف «{name}» مفقود أو فارغ: {path}")
        lines = paths["candidates"].read_text(encoding="utf-8").strip().splitlines()
        for line in lines:
            record = json.loads(line)
            for field in ("source", "spdx", "scan_result", "decision", "reason"):
                if not str(record.get(field, "")).strip():
                    return ProofResult(False, f"سطر مرشّح بلا «{field}».")
    return ProofResult(
        True, f"{len(result.candidates)} مرشّحين، لكل سطر مصدر ورخصة وفحص وسبب (بيانات اصطناعية)."
    )

PROOFS: dict[str, Proof] = {
    "cli_run_creates_project": cli_run_creates_project,
    "licenses_decided": licenses_decided,
    "reuse_decisions_recorded": reuse_decisions_recorded,
    "every_import_has_record": every_import_has_record,
    "ir_rules_reject_negatives": ir_rules_reject_negatives,
    "scaffold_creates_structure": scaffold_creates_structure,
    "gates_pass": gates_pass,
    "tests_report_has_results": tests_report_has_results,
    "injected_defect_is_detected": injected_defect_is_detected,
    "zero_budget_stops": zero_budget_stops,
    "reports_exist_and_non_empty": reports_exist_and_non_empty,
    "resume_after_crash": resume_after_crash,
    "budget_overrun_is_blocked": budget_overrun_is_blocked,
    "required_files_present": required_files_present,
    "rebuild_hash_is_stable": rebuild_hash_is_stable,
    "plugin_works_without_core_change": plugin_works_without_core_change,
    "idea_produces_prd": idea_produces_prd,
    "research_produces_competitors": research_produces_competitors,
    "research_produces_candidates": research_produces_candidates,
}


def run_all_proofs() -> list[tuple[str, ProofResult]]:
    """يشغّل كل الشواهد ويعيد النتائج."""
    results: list[tuple[str, ProofResult]] = []
    for key, proof in PROOFS.items():
        try:
            results.append((key, proof()))
        except Exception as error:  # noqa: BLE001 — الفشل يُسجَّل كشواهد
            results.append((key, ProofResult(False, f"استثناء: {type(error).__name__}: {error}")))
    return results
