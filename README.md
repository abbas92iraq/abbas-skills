# abbas skills

أرشيف منظّم لمهارات الوكلاء (**Agent Skills**) المأخوذة من [skills.sh](https://www.skills.sh/)، لاستخدامها كمرجع داخل المحادثات مع Claude Code وبقية وكلاء البرمجة.

🔄 **يُحدَّث تلقائيًا كل يوم** الساعة ٦ صباحًا بتوقيت بغداد عبر GitHub Actions.

## 📄 الملف الرئيسي

### 👉 [`abbas-skills.md`](./abbas-skills.md)

| المحتوى | العدد |
|---|---:|
| مهارات موثّقة بالتفصيل الكامل | **500** |
| مهارات في الفهرس السريع | **600** |
| منها مهارات رسمية (Official) | **139** |
| إجمالي المهارات المتاحة على skills.sh | **9,684** |
| آخر تحديث | **2026-08-26** |

## ✅ ما الذي يحتويه كل سجل؟

- **الاسم** والمستودع المصدر
- **أمر التثبيت** الجاهز للنسخ (`npx skills add ...`)
- **الوصف** وأبرز القدرات
- **الأداء**: عدد التثبيتات · اتجاه آخر ٨ أسابيع · نجوم GitHub · تاريخ أول ظهور
- **نتائج الفحص الأمني** (Gen Agent Trust Hub · Socket · Snyk)
- **روابط** صفحة المهارة والمستودع

## 🚀 الاستخدام السريع

```bash
# تثبيت مهارة واحدة
npx skills add https://github.com/anthropics/skills --skill pdf

# تثبيت كل مهارات مستودع
npx skills add vercel-labs/skills
```

داخل المحادثة مع الوكيل:

> «راجع `abbas-skills.md` واختر لي مهارة مناسبة لـ ... ثم ثبّتها.»

## ⚙️ آلية التحديث

| الملف | الوظيفة |
|---|---|
| [`scripts/build_archive.py`](./scripts/build_archive.py) | يسحب البيانات من skills.sh ويعيد بناء الأرشيف |
| [`.github/workflows/daily-update.yml`](./.github/workflows/daily-update.yml) | يشغّل السكربت يوميًا ويرفع التغييرات |
| [`data/skills.json`](./data/skills.json) | لقطة البيانات، تُستخدم لرصد الداخل والخارج من القائمة |
| [`CHANGELOG.md`](./CHANGELOG.md) | سجل التغييرات اليومي |

للتشغيل اليدوي: تبويب **Actions** ← **Daily skills archive update** ← **Run workflow**.

---

**المصدر:** https://www.skills.sh/
