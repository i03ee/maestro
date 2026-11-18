# سجل المصادر: من أين جاء كل سطر

سجل حيّ. كل بند هنا يمرّ على بوابة `scripts/check_licenses.py` أو يُسجَّل في
`docs/provenance/dependencies.json` بقرار صريح.

## بنود الحصاد

| المكوّن | المصدر | الترخيص | القرار | السبب |
|---|---|---|---|---|
| Saleor API | https://github.com/saleor/saleor | BSD-3-Clause | قبول عبر API | محرّك تجارة مثبت؛ لا ننسخ شيفرته |
| Nimara | https://github.com/mirumee/nimara-ecommerce | BSD-3-Clause | مراجع، غير مدمج | نمط واجهة جيد، لكن سطح تبعيات كبير |
| Saleor Storefront | https://github.com/saleor/storefront | FSL-1.1 | **رفض** | قيد تنافسي يمنع الاستعمال التجاري |
| k6 | https://github.com/grafana/k6 | AGPL-3.0 | **رفض** | ترخيص نسخ قسري (copyleft)؛ طبقة الحمل تستعمل Locust (MIT) |
| MobSF | https://github.com/MobSF/Mobile-Security-Framework-MobSF | GPL-3.0 | **خدمة معزولة فقط** | لا دمج؛ مخرجاته ملفات مدقّقة |
| Frida | https://github.com/frida/frida | non-OSI | **رفض** | رخصة خارج OSI |
| PydanticAI | https://github.com/pydantic/pydantic-ai | MIT | قبول | نواة الوكلاء |
| Locust | https://github.com/locustio/locust | MIT | قبول | بديل k6 لطبقة الحمل |

## قاعدة الاستخراج

الاستخراج على مستوى **الملف والدالة**، لا المشروع:

1. ملف واحد يُنسخ من مشروع خارجي يحمل في رأسه: رخصة المصدر، عنوانه، ونطاق
   ما أُخذ بالضبط.
2. كل استيراد يمرّ على **اختبار عقد** يثبت السلوك المتوقع قبل الاستخدام.
3. السجل هنا يُحدَّث في نفس طلب الدمج الذي يجلب الاستخراج — لا بعده.

## مستودعات المستخدم (حصاد 2026-11-18)

| المستودع | الحالة | القرار |
|---|---|---|
| `i03ee/maestro` | فارغ عند بداية الحصاد | صار مستودع النواة (هذا المستودع) |
| `i03ee/iraq-beauty-commerce` | نَسمة: Next.js + Expo + Saleor، رخصة MIT | **العميل الأول للشركة** — منفصل، ويستخدم هذه النواة |

تفاصيل حصاد «نَسمة» في [`../harvest/001-nasma.md`](../harvest/001-nasma.md).
