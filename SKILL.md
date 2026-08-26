---
name: abbas-skills
description: Find and install the right agent skill for a task. Use whenever the user asks "is there a skill for X", wants a capability the agent lacks (PDF handling, video generation, design review, database work, marketing, testing, browser automation), or asks what skills are available. Searches a curated, deduplicated archive of the top agent skills on skills.sh with install commands, popularity data, and security-audit results.
---

# مرجع مهارات الوكلاء (abbas skills)

أرشيف تراكمي منقّى لأقوى مهارات الوكلاء على [skills.sh](https://www.skills.sh/)،
مع أوامر التثبيت ومؤشرات الأداء ونتائج الفحص الأمني.

## متى تستخدم هذه المهارة

- المستخدم يسأل: «هل توجد مهارة لـ...؟» أو «ابحث لي عن skill لـ...»
- المهمة تحتاج قدرة لا يملكها الوكيل حاليًا (معالجة PDF، توليد فيديو، أتمتة متصفح، مراجعة تصميم…)
- المستخدم يسأل عن المهارات المتاحة أو الأكثر شعبية

## طريقة العمل

**١. ابحث في الفهرس المضغوط أولًا — لا تقرأ الأرشيف كاملًا.**

`abbas-skills.md` كبير جدًا (أكثر من ميغابايت). قراءته كاملة تستهلك السياق بلا داعٍ.
ابدأ دائمًا بـ `INDEX.md`، وهو سطر واحد لكل مهارة:

```bash
grep -i -A2 "pdf\|document" INDEX.md | head -40
```

**٢. اقرأ البطاقة الكاملة للمرشّحات فقط:**

```bash
grep -n -A20 "^### [0-9]*\. pdf$" abbas-skills.md
```

**٣. رشّح بناءً على المعطيات:**

| المؤشر | القاعدة |
|---|---|
| **التثبيتات** | فضّل الأعلى — مؤشر نضج وموثوقية |
| **⭐ رسمية** | فضّلها عند تساوي الباقي (من مطوّر التقنية نفسه) |
| **الاتجاه 📈** | نموّ مستمر = صيانة نشطة |
| **الفحص الأمني** | تجنّب `Fail`؛ نبّه المستخدم عند `Warn` |
| **📌** | بياناتها قد تكون قديمة — تحقّق من صفحتها |

**٤. اعرض ٢-٣ خيارات مع سبب الترشيح، ثم ثبّت ما يختاره المستخدم:**

```bash
npx skills add https://github.com/anthropics/skills --skill pdf
```

## قواعد مهمة

- **لا تخترع** أسماء مهارات أو أوامر تثبيت — انسخها حرفيًا من الأرشيف.
- إن لم تجد شيئًا مناسبًا، قل ذلك واقترح البحث المباشر في https://www.skills.sh/ —
  الأرشيف يغطي الأقوى فقط، لا كل المهارات الموجودة على الموقع.
- **نبّه المستخدم** قبل تثبيت مهارة نتيجة فحصها الأمني `Fail`.
- الأرقام لقطة يومية وقد تتغيّر.

## الملفات

| الملف | المحتوى |
|---|---|
| `INDEX.md` | فهرس مضغوط — **ابدأ من هنا** |
| `abbas-skills.md` | البطاقات التفصيلية الكاملة |
| `DUPLICATES.md` | المهارات المكرّرة المحذوفة ولماذا |
| `CHANGELOG.md` | الجديد يوميًا |
