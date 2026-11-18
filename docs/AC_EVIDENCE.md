# دليل معايير القبول AC-01..AC-20

> وثيقة **مولَّدة** من `src/maestro/acceptance/criteria.py`.
> النتائج الحيّة تُشغَّل بـ`python3 scripts/verify_acceptance.py`.

معايير لها شاهد منفَّذ: **17** من 20 — والمتبقّي **3** غير مُثبَت بعد (مع سبب النقص).

| المعيار | العنوان | الدليل المسمّى | الحالة | الشاهد |
|---|---|---|---|---|
| AC-01 | استقبال فكرة | `cli/run_request.json` | مُثبَت | `cli_run_creates_project` |
| AC-02 | تحويل الفكرة إلى متطلبات | `artifacts/prd.md, user_stories.json` | غير مُثبَت بعد | لا يوجد بعد مُنتِج متطلبات: قدرة idea_framing ماسَجة في الكتالوج ولم تُنفَّذ بعد. |
| AC-03 | تحليل منافسين | `artifacts/market/competitor_matrix.csv` | غير مُثبَت بعد | يتطلّب بحثاً حيّاً بمصدر لكل صف — لم يُنفَّذ بعد. |
| AC-04 | البحث عن مكونات | `artifacts/research/candidates.jsonl` | غير مُثبَت بعد | يتطلّب تنفيذ قدرة البحث بمزوّد حيّ — لم يُنفَّذ بعد. |
| AC-05 | تقييم التراخيص والتبعيات | `artifacts/research/scans/` | مُثبَت | `licenses_decided` |
| AC-06 | تسجيل قرارات إعادة الاستخدام | `artifacts/decisions/decision_log.jsonl` | مُثبَت | `reuse_decisions_recorded` |
| AC-07 | AppIR قابل للتحقق | `appir/appir.json + validate_report.json` | مُثبَت | `ir_rules_reject_negatives` |
| AC-08 | إنشاء مشروع من قالب | `workspace/ + build logs` | مُثبَت | `scaffold_creates_structure` |
| AC-09 | دمج مكونات | `provenance.jsonl` | مُثبَت | `every_import_has_record` |
| AC-10 | بناء بلا أخطاء حرجة | `reports/build.json` | مُثبَت | `gates_pass` |
| AC-11 | تشغيل الاختبارات وتسجيل النتائج | `reports/tests.json` | مُثبَت | `tests_report_has_results` |
| AC-12 | اكتشاف الأخطاء وإصلاحها | `reports/repair.json` | مُثبَت | `injected_defect_is_detected` |
| AC-13 | إيقاف العمليات الخطرة | `reports/escalation.json` | مُثبَت | `zero_budget_stops` |
| AC-14 | فحص مستقل | `reports/inspector_report.md` | مُثبَت | `injected_defect_is_detected` |
| AC-15 | تقارير جودة وأمان وتراخيص | `reports/{quality,security,license}.md` | مُثبَت | `reports_exist_and_non_empty` |
| AC-16 | حفظ الحالة والاستئناف | `state.json + run_events` | مُثبَت | `resume_after_crash` |
| AC-17 | إدارة الميزانية | `reports/costs.json` | مُثبَت | `budget_overrun_is_blocked` |
| AC-18 | تسليم الملفات والتوثيق | `docs/ + artifacts/` | مُثبَت | `required_files_present` |
| AC-19 | إعادة البناء من الإصدارات | `provenance + lockfiles` | مُثبَت | `rebuild_hash_is_stable` |
| AC-20 | إضافة محركات دون إعادة بناء | `examples/plugin_minimal/` | مُثبَت | `plugin_works_without_core_change` |

## المعايير غير المُثبَتة بعد

- **AC-02 — تحويل الفكرة إلى متطلبات**: لا يوجد بعد مُنتِج متطلبات: قدرة idea_framing ماسَجة في الكتالوج ولم تُنفَّذ بعد.
- **AC-03 — تحليل منافسين**: يتطلّب بحثاً حيّاً بمصدر لكل صف — لم يُنفَّذ بعد.
- **AC-04 — البحث عن مكونات**: يتطلّب تنفيذ قدرة البحث بمزوّد حيّ — لم يُنفَّذ بعد.

## اختبار الحقن (AC-12 وAC-14)

نحقن عيباً متعمّداً في **نسخة** من الشيفرة — نحذف فحص الصلاحية في `guards/permission.py` — ثم نطالب المفتّش بأن يرفض النسخة المعطوبة ويقبل السليمة. إن قبل المعطوبة ⇒ النظام غير جاهز. هذا هو اختبار القبول رقم واحد في وثيقة المتطلبات.

