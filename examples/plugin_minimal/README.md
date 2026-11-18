# مثال محرّك جديد

هنا تُثبت القاعدة **AC-20**: إضافة محرّك (نموذج، مزوّد، أو أي تنفيذ) يجب أن
تكون **ملف تعريف** لا إعادة بناء.

## ما المطلوب

1. صنف يلتزم واجهة `Provider`:
   ```python
   def complete(self, request: CompletionRequest, profile: ModelProfile) -> CompletionResponse
   ```
2. تمريره إلى `ModelRouter(providers={...}, profiles={...})`.

## ما لا يُطلب

- لا تعديل في `src/maestro/` إطلاقاً.
- لا تعديل في السجل أو الحرّاس أو العقد.
- لا تثبيت حزمة.

## الفحص

شاهد القبول `plugin_works_without_core_change` في
`src/maestro/acceptance/proofs.py` يحمّل هذا الملف من مساره ويشغّله عبر
الموجّه — ويفشل إن احتاج المثال تعديل النواة.
