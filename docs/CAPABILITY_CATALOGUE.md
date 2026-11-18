# كتالوج الشركة

> وثيقة **مولَّدة** من `src/maestro/company/catalogue.py`.
> لا تُحرَّر بيد: `python3 scripts/catalogue_report.py --check`
> يفشل البوابة إن انحرف محتوى هذه الصفحة عن الشيفرة.

## القواعد الخمس الحاكمة

1. **مركز واحد، ذراعان.** نقطة مركزية واحدة تدير النطاقات الثمانية، ومعاها مساعد التحليل ومساعد التحقق. لا مركزان.
2. **ثمانية نطاقات، لا 24 وكيلاً متقطعاً.** كل نطاق مديره واحد يملك ميزانيته وصلاحياته، ويصدر «قرار نطاق» يُعتمد من المركز.
3. **الاعتماد المتبادل بدل التسلسل.** البوابات ليست في آخر الطريق: بوابة الفكرة تسبق البناء، وبوابة الواجهة تسبق التسليم، وبوابة التسعير تسبق الحدود، وبوابة الدفع تسبق الإصدار.
4. **قدرة واحدة = وكيل واحد = عقد واحد.** من يحتاج ذاكرة خاصة فهو **استدعاء إضافي** لقدرة موجودة، لا قدرة جديدة.
5. **القدرة الحرجة لا تُقبل بنموذج واحد.** تُنفَّذ بنموذجين مستقلين ويُقبل الناتج باتفاقهما — شرط قابل للاختبار لا انطباع.

## الأرقام

- النطاقات: **8**
- القدرات: **24**
- البوابات: **11**
- وصلات الاعتماد: **17**
- القدرات الحرجة: **7**
- مواضع استدعاء بوابة المجتمع: **4**

## النطاقات

| النطاق | المهمة | المدير | القدرات |
|---|---|---|---|
| التجاري (`commercial`) | من الفكرة إلى النموذج المالي والتسعير المبرَّر | `commercial_director` | 4 |
| المجتمع (`community`) | اختبار المجتمع: لوحة شرائح تُستدعى في أربعة مواضع من الطريق | `community_director` | 1 |
| البحث والاختيار (`research`) | ترشيح المشاريع وتقييمها واختيار واحد | `research_director` | 3 |
| الهندسة (`engineering`) | مراجعة الكود ودمجه واختباره وواجهات الدفع | `engineering_director` | 4 |
| التجربة (`experience`) | التصميم وبناء الواجهة ومراجعتها | `experience_director` | 3 |
| الجودة (`quality`) | فحص أمني وضغط وامتثال | `quality_director` | 4 |
| الإصدار (`release`) | فحص الإصدار وتوقيعه ونشره ومراقبته | `release_director` | 3 |
| البيانات والقوالب (`data`) | خطوط بيانات المنتج وقوالب التطبيقات الثلاث | `data_director` | 2 |

## القدرات

| القدرة | الوكيل | صلاحية | حرجة | النموذج ١ | شرط النقل | البوابات |
|---|---|---|---|---|---|---|
| `commercial.idea_framing`<br/>صياغة الفكرة وعرضها على لوحة المجتمع | `idea_framer` | 1 | لا | `local` | تشابه الفكرة مع فكرة أخرى أو خروج بلا بنية | `community.community_test` |
| `commercial.market_research`<br/>بحث السوق والمنافسين | `market_researcher` | 1 | لا | `local` | تعذّر الوصول إلى المصدر أو ردّ بلا أدلة | — |
| `commercial.business_model`<br/>نموذج العمل ومسار الإيراد | `model_builder` | 2 | لا | `local` | فشل النموذج أو خروجه بمخرج فارغ | — |
| `commercial.pricing`<br/>التسعير المبرَّر برقم | `pricer` | 2 | نعم | `api` | تباين رقمي فوق 10% بين نموذجين | `community.community_test`، `quality.compliance_review` |
| `community.community_test`<br/>اختبار المجتمع — بوابة واحدة بأربعة استدعاءات | `community_tester` | 2 | نعم | `api` | انخفاض قبول اللوحة تحت الحدّ أو تعذّر تشغيل اللوحة | — |
| `research.project_research`<br/>بحث المشروع ومصدره ورخصته | `project_researcher` | 1 | لا | `local` | فشل التحقق من الترخيص أو المصدر | — |
| `research.project_evaluation`<br/>تقييم المشروع بمعيار معلن | `project_evaluator` | 1 | لا | `local` | فشل النموذج أو خروجه بمخرج فارغ | — |
| `research.project_selection`<br/>اختيار مشروع واحد وبتعليل مكتوب | `project_selector` | 2 | لا | `local` | فشل النموذج أو خروجه بمخرج فارغ | `research.project_evaluation` |
| `engineering.code_review`<br/>مراجعة الكود وفحص الثغرات | `code_reviewer` | 1 | نعم | `local` | ثقة أقل من 0.7 أو خطأ أداة | — |
| `engineering.code_merge`<br/>الدمج بعد اجتياز المراجعة والاختبار | `code_merger` | 1 | لا | `local` | فشل النموذج أو خروجه بمخرج فارغ | `engineering.code_review`، `engineering.code_test` |
| `engineering.code_test`<br/>كتابة الاختبارات وتشغيلها | `test_engineer` | 1 | لا | `local` | فشل النموذج أو خروجه بمخرج فارغ | — |
| `engineering.payment_interface`<br/>واجهة الدفع والعقود | `payment_engineer` | 3 | نعم | `local` | رفض المزوّد أو ردّ بلا توقيع | `community.community_test`، `quality.data_security` |
| `experience.ui_design`<br/>تصميم الواجهة والأيقونات | `ui_designer` | 1 | لا | `local` | فشل النموذج أو خروجه بمخرج فارغ | — |
| `experience.ui_build`<br/>بناء الواجهة | `ui_builder` | 1 | لا | `local` | فشل النموذج أو خروجه بمخرج فارغ | `community.community_test`، `experience.ui_review` |
| `experience.ui_review`<br/>مراجعة الواجهة وقبولها | `ui_reviewer` | 1 | لا | `local` | فشل النموذج أو خروجه بمخرج فارغ | — |
| `quality.data_security`<br/>فحص أمن البيانات والصلاحيات | `security_inspector` | 1 | نعم | `local` | نتيجة غير حاسمة | — |
| `quality.penetration_test`<br/>اختبار الاختراق | `penetration_tester` | 2 | لا | `local` | فشل النموذج أو خروجه بمخرج فارغ | — |
| `quality.load_test`<br/>اختبار الحمل والضغط | `load_tester` | 1 | لا | `local` | تجاوز حدّ المدة أو فشل نقطةHealth | — |
| `quality.compliance_review`<br/>مراجعة الامتثال وسياسات المنصة | `compliance_reviewer` | 2 | لا | `local` | فشل النموذج أو خروجه بمخرج فارغ | — |
| `release.release_qa`<br/>فحص الإصدار النهائي | `release_inspector` | 1 | لا | `local` | فشل النموذج أو خروجه بمخرج فارغ | `engineering.code_test`، `quality.load_test` |
| `release.release_signing`<br/>توقيع حزمة الإصدار | `release_signer` | 3 | لا | `local` | فشل النموذج أو خروجه بمخرج فارغ | `release.release_qa` |
| `release.release_publish`<br/>النشر والمراقبة | `release_publisher` | 3 | نعم | `local` | فشل النشر أو فشل فحص الصحة بعد النشر | `release.release_signing`، `quality.data_security` |
| `data.data_pipeline`<br/>خط بيانات المنتج: من ملف المورّد إلى منشور | `data_pipeline` | 2 | نعم | `local` | خلل في عقد الردّ أو في شكل المدخل | `quality.compliance_review` |
| `data.app_template`<br/>قوالب web وandroid وios | `template_builder` | 1 | لا | `local` | فشل النموذج أو خروجه بمخرج فارغ | `research.project_selection` |

## بوابة المجتمع: قدرة واحدة، أربعة استدعاءات

البوابة: `community.community_test` — قدرة واحدة بذاكرة واحدة.

1. `commercial.idea_framing`
2. `experience.ui_build`
3. `commercial.pricing`
4. `engineering.payment_interface`

## شبكة الاعتماد

| يحتاج | بوابته |
|---|---|
| `commercial.idea_framing` | `community.community_test` |
| `commercial.pricing` | `community.community_test` |
| `commercial.pricing` | `quality.compliance_review` |
| `data.app_template` | `research.project_selection` |
| `data.data_pipeline` | `quality.compliance_review` |
| `engineering.code_merge` | `engineering.code_review` |
| `engineering.code_merge` | `engineering.code_test` |
| `engineering.payment_interface` | `community.community_test` |
| `engineering.payment_interface` | `quality.data_security` |
| `experience.ui_build` | `community.community_test` |
| `experience.ui_build` | `experience.ui_review` |
| `release.release_publish` | `quality.data_security` |
| `release.release_publish` | `release.release_signing` |
| `release.release_qa` | `engineering.code_test` |
| `release.release_qa` | `quality.load_test` |
| `release.release_signing` | `release.release_qa` |
| `research.project_selection` | `research.project_evaluation` |

