# دليل معايير القبول AC-01..AC-20

> وثيقة **مولَّدة** من `src/maestro/acceptance/criteria.py`.
> النتائج الحيّة تُشغَّل بـ`python3 scripts/verify_acceptance.py`.

معايير لها شاهد منفَّذ: **20** من 20 — والمتبقّي **0** غير مُثبَت بعد (مع سبب النقص).

**نوع الشاهد** يفرّق بين شاهدين حيّين (بيانات حقيقية) وشاهد آلية (الآلية مُتحقَّقة ببيانات اصطناعية، والبيانات الحيّة معلّقة حتى يصل مفتاح المزوّد).

| المعيار | العنوان | الدليل المسمّى | الحالة | الشاهد |
|---|---|---|---|---|
| AC-01 | استقبال فكرة | `cli/run_request.json` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `cli_run_creates_project` |
| AC-02 | تحويل الفكرة إلى متطلبات | `artifacts/prd.md, user_stories.json` | مُثبَت — بشواهد آلية — البيانات الحيّة معلّقة (تحتاج DEEPSEEK_API_KEY) | `idea_produces_prd` |
| AC-03 | تحليل منافسين | `artifacts/market/competitor_matrix.csv` | مُثبَت — بشواهد آلية — البيانات الحيّة معلّقة (تحتاج DEEPSEEK_API_KEY) | `research_produces_competitors` |
| AC-04 | البحث عن مكونات | `artifacts/research/candidates.jsonl` | مُثبَت — بشواهد آلية — البيانات الحيّة معلّقة (تحتاج DEEPSEEK_API_KEY) | `research_produces_candidates` |
| AC-05 | تقييم التراخيص والتبعيات | `artifacts/research/scans/` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `licenses_decided` |
| AC-06 | تسجيل قرارات إعادة الاستخدام | `artifacts/decisions/decision_log.jsonl` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `reuse_decisions_recorded` |
| AC-07 | AppIR قابل للتحقق | `appir/appir.json + validate_report.json` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `ir_rules_reject_negatives` |
| AC-08 | إنشاء مشروع من قالب | `workspace/ + build logs` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `scaffold_creates_structure` |
| AC-09 | دمج مكونات | `provenance.jsonl` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `every_import_has_record` |
| AC-10 | بناء بلا أخطاء حرجة | `reports/build.json` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `gates_pass` |
| AC-11 | تشغيل الاختبارات وتسجيل النتائج | `reports/tests.json` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `tests_report_has_results` |
| AC-12 | اكتشاف الأخطاء وإصلاحها | `reports/repair.json` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `injected_defect_is_detected` |
| AC-13 | إيقاف العمليات الخطرة | `reports/escalation.json` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `zero_budget_stops` |
| AC-14 | فحص مستقل | `reports/inspector_report.md` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `injected_defect_is_detected` |
| AC-15 | تقارير جودة وأمان وتراخيص | `reports/{quality,security,license}.md` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `reports_exist_and_non_empty` |
| AC-16 | حفظ الحالة والاستئناف | `state.json + run_events` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `resume_after_crash` |
| AC-17 | إدارة الميزانية | `reports/costs.json` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `budget_overrun_is_blocked` |
| AC-18 | تسليم الملفات والتوثيق | `docs/ + artifacts/` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `required_files_present` |
| AC-19 | إعادة البناء من الإصدارات | `provenance + lockfiles` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `rebuild_hash_is_stable` |
| AC-20 | إضافة محركات دون إعادة بناء | `examples/plugin_minimal/` | مُثبَت — بشواهد حيّة تُنفَّذ في كل تشغيل | `plugin_works_without_core_change` |

## المعايير غير المُثبَتة بعد


## اختبار الحقن (AC-12 وAC-14)

نحقن عيباً متعمّداً في **نسخة** من الشيفرة — نحذف فحص الصلاحية في `guards/permission.py` — ثم نطالب المفتّش بأن يرفض النسخة المعطوبة ويقبل السليمة. إن قبل المعطوبة ⇒ النظام غير جاهز. هذا هو اختبار القبول رقم واحد في وثيقة المتطلبات.

