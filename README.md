# abbas skills

أرشيف تراكمي منقّى لمهارات الوكلاء (**Agent Skills**) من [skills.sh](https://www.skills.sh/) — مرجع جاهز للاستخدام داخل المحادثات مع Claude Code وبقية وكلاء البرمجة.

🔄 **تحديث تلقائي يومي** · ➕ **تراكمي** · 🧹 **بلا تكرار**

## 📄 الملفات

| الملف | الوظيفة |
|---|---|
| [`abbas-skills.md`](./abbas-skills.md) | الأرشيف الكامل — بطاقة تفصيلية لكل مهارة |
| [`INDEX.md`](./INDEX.md) | فهرس مضغوط سطر لكل مهارة — للبحث السريع |
| [`CHANGELOG.md`](./CHANGELOG.md) | سجل يومي بالمهارات الجديدة |
| [`DUPLICATES.md`](./DUPLICATES.md) | تقرير التكرارات المحذوفة |
| [`SKILL.md`](./SKILL.md) | يجعل المستودع نفسه مهارة قابلة للتثبيت |

## 📊 الأرقام

| | |
|---|---:|
| المهارات في الأرشيف | **952** |
| نطاق المتابعة اليومية | **أعلى 1,000** |
| مهارات محفوظة خارج النطاق 📌 | **0** |
| مهارات رسمية ⭐ | **313** |
| مكرّرات محذوفة 🧹 | **48** |
| إجمالي المهارات على skills.sh | **9,684** |
| آخر تحديث | **2026-08-26** |

## 🆕 أحدث الإضافات

- **signup** — `coreyhaines31/marketingskills` (48,913 تثبيت)
- **free-tools** — `coreyhaines31/marketingskills` (48,904 تثبيت)
- **aso** — `coreyhaines31/marketingskills` (48,895 تثبيت)
- **referrals** — `coreyhaines31/marketingskills` (48,849 تثبيت)
- **web-search** — `skills-101/superpowers` (48,529 تثبيت)
- **popups** — `coreyhaines31/marketingskills` (48,459 تثبيت)
- **paywalls** — `coreyhaines31/marketingskills` (48,399 تثبيت)
- **agent-tools** — `skills-101/superpowers` (48,366 تثبيت)
- **infsh-cli** — `skills-101/superpowers` (48,352 تثبيت)
- **python-executor** — `skills-101/superpowers` (48,316 تثبيت)

السجل الكامل في [`CHANGELOG.md`](./CHANGELOG.md).

## 🤖 استخدامه كمساعد افتراضي

**الطريقة الأولى — تثبيته كمهارة** (يجعل الوكيل يستشير الأرشيف تلقائيًا):

```bash
npx skills add abbas92iraq/abbas-skills
```

**الطريقة الثانية — إضافته لذاكرة Claude Code الدائمة:**

```bash
git clone https://github.com/abbas92iraq/abbas-skills ~/abbas-skills
```

ثم أضف هذا إلى `~/.claude/CLAUDE.md`:

```markdown
## مرجع المهارات
عند الحاجة إلى مهارة (skill) لأي مهمة، ابحث أولًا في `~/abbas-skills/INDEX.md`،
ثم اقرأ البطاقة الكاملة من `~/abbas-skills/abbas-skills.md` ونفّذ أمر التثبيت.
لا تقرأ `abbas-skills.md` كاملًا — ابحث فيه بكلمة مفتاحية.
```

**الطريقة الثالثة — في جلسات Claude Code على الويب:** أضف المستودع كمصدر (Source) للبيئة، فيصبح متاحًا في كل جلسة جديدة.

## ⚙️ آلية التحديث

يوميًا **06:00 صباحًا بتوقيت بغداد** عبر [GitHub Actions](./.github/workflows/daily-update.yml):

1. سحب أعلى **1,000** مهارة من لوحة صدارة skills.sh
2. جلب صفحة كل مهارة واستخراج الوصف والأداء والفحص الأمني
3. **الدمج التراكمي** مع الأرشيف — لا تُحذف أي مهارة بسبب تراجع ترتيبها
4. **كشف التكرار** — دمج المهارات ذات العمل نفسه وإبقاء الأقوى
5. إعادة بناء الملفات ورفع commit عند وجود تغيير فقط

للتشغيل اليدوي: تبويب **Actions** ← **Daily skills archive update** ← **Run workflow**.

---

**المصدر:** https://www.skills.sh/
