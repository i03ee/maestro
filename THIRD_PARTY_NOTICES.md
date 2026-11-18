# إشعارات الأطراف الثالثة

هذا الملف سجل لكل كود أو خدمة خارجية رُوجعت في مشروع MAESTRO. القاعدة:
**نقبل الكود، نرفض الترخيص** — لا يدخل المستودع إلا ما كانت رخصته تسمح
بالاستعمال والتوزيع داخل مشروع مملوك.

## مُراجَع ومُعتمد

| المكوّن | الترخيص | المصدر | القرار | أين يُستخدم |
|---|---|---|---|---|
| PydanticAI (pydantic-ai-slim) | MIT | https://github.com/pydantic/pydantic-ai | قبول | طبقة تنفيذ الوكلاء |
| Saleor API | BSD-3-Clause | https://github.com/saleor/saleor | قبول عبر واجهة برمجية | محرّك التجارة في نَسمة |
| Nimara e-commerce | BSD-3-Clause | https://github.com/mirumee/nimara-ecommerce | مراجع، غير مدمج | نمط واجهة للدراسة |
| Locust | MIT | https://github.com/locustio/locust | قبول | طبقة الحمل بدل k6 |
| setuptools | MIT | https://github.com/pypa/setuptools | قبول | أداة البناء فقط؛ لا تدخل الكود المشغَّل |

## مرفوض

| المكوّن | الترخيص | السبب |
|---|---|---|
| k6 | AGPL-3.0 | ترخيص نسخ قسري (copyleft)؛ يُستبدل بـ Locust |
| MobSF | GPL-3.0 | عزل كخدمة داخلية فقط، لا دمج |
| Frida | non-OSI | رخصة غير معتمدة من OSI |
| Saleor Storefront | FSL-1.1 | قيد تنافسي يمنع الاستعمال التجاري |

## مراجعة مقترحة

- كل سطر مستعار من مشروع خارجي يحمل في نفس الملف رخصة المصدر وعنوانه.
- كل دمج يمرّ على بوابة `scripts/check_licenses.py` وعلى سجل العقود.
