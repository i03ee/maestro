# دليل التشغيل

هذا الدليل لـ**من يشغّل** المستودع: من يستنسخه، وكيف يبني، وكيف يفحص،
وكيف يتصرّف عند الفشل. كل أمر هنا مُختبَر في خط الأنابيب.

## المتطلبات

| الأداة | النسخة | لماذا |
|---|---|---|
| Python | 3.11 أو 3.12 | النواة. بلا تبعيات وقت تشغيل. |
| Git | 2.30+ | العمل على المستودع. |
| (اختياري) مفتاح مزوّد | `DEEPSEEK_API_KEY` | التشغيل الحيّ فقط. |

**لا يوجد** `pip install` إلزامي. النواة تعمل من المكتبة القياسية.
مجموعة الوكلاء الحيّة اختيارية: `pip install -e ".[agent]"` (تحتاج PyPI).

## التشغيل من الصفر

```bash
git clone https://github.com/i03ee/maestro.git
cd maestro
python3 scripts/validate_repo.py        # ثوابت المستودع
python3 scripts/check_licenses.py       # بوابة التراخيص
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## البوابات الستّ

| البوابة | الأمر | ماذا تفشل فيه |
|---|---|---|
| ثوابت المستودع | `scripts/validate_repo.py` | ملف أساسي مفقود، سرّ، محرف مسرّب، شيفرة لا تُصرَّف، خط أنابيب متسامح، كتالوج غير متّسق، انحراف وثيقة |
| التراخيص | `scripts/check_licenses.py` | تبعية بلا قرار مسجَّل، أو تبعية مرفوضة |
| الكتالوج | `scripts/catalogue_report.py --check` | انحراف وثيقة الكتالوج عن الشيفرة |
| القبول | `scripts/verify_acceptance.py` | شاهد معيار قبول فاشل |
| التقييم | `scripts/eval_check.py` | حالة تقييم لا تطابق المواصفة |
| الحمل | `scripts/load_check.py` | خطأ واحد، أو p95 فوق السقف |

كلها **ثنائية**: تجتاز أو تفشل. لا عتبات نسبية.

## أوامر التشغيل

```bash
# استقبال فكرة
PYTHONPATH=src python3 -m maestro run "فكرة" --out cli

# إنشاء هيكل مشروع
PYTHONPATH=src python3 -m maestro scaffold --out workspace

# تنفيذ قدرة بالمزوّد الحقيقي
python3 scripts/run_capability.py --ir task.json --out artifacts/

# فحص مستند IR بلا نموذج
python3 scripts/run_capability.py --ir task.json --check

# تسجيل قياس الخط الأساسي البشري
python3 scripts/capture_baseline.py --capability catalog.ingest \
    --output-id sku-001 --human-minutes 12 --accepted-unedited yes

# تجميع حزمة التسليم
python3 scripts/build_delivery_pack.py --out dist/
```

## عند الفشل

| العَرَض | السبب المحتمل | الإجراء |
|---|---|---|
| `محرف مسرّب` | حرف صيني/كوري تسلّل إلى نص | احذفه: البوابة تحدّد الملف والصف |
| `انحراف بين الوثيقة والشيفرة` |تغيّر الكتالوج دون توليد الوثيقة | `python3 scripts/catalogue_report.py` |
| `انحراف بين وثيقة القبول والشيفرة` | تغيّر جدول المعايير | `python3 scripts/verify_acceptance.py --write-docs` |
| `تبعية غير مسجّلة` | تبعية جديدة بلا قرار | أضف القرار في `docs/provenance/dependencies.json` |
| `شاهد فاشل` | تراجع في معيار | اقرأ سطر التفاصيل في التقرير — يذكر السبب |
| `العيب المحقون غير مرصود` | **المختبِر نفسه معطوب** | هذا أخطر خطأ: حقن العيب لم يغيّر السلوك ⇒ افحص الاختبار قبل النظام |

## التشغيل الحيّ

```bash
export DEEPSEEK_API_KEY=...      # في مدير الأسرار، لا في المستودع
pip install -e ".[agent]"       # طبقة الوكلاء
PYTHONPATH=src python3 -m maestro run "فكرة" --out cli
```

بلا مفتاح: يرفض المزوّد **قبل** إرسال أي طلب، ولا يُكتب سرّ ولا في السجل.

## ما لا يُصلَح محلياً

- **PyPI محجوب** في بعض البيئات ⇒ المجموعة الاختيارية لا تُثبَّت محلياً؛
  اختبارات الطبقة الحيّة تعمل في CI حيث Package متاح.
- **ترخيص جديد** ⇒ بوابة التراخيص ترفضه. لا تجاوز: «نقبل الكود، نرفض الترخيص».
