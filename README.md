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
| المهارات في الأرشيف | **996** |
| نطاق المتابعة اليومية | **أعلى 1,000** |
| مهارات محفوظة خارج النطاق 📌 | **45** |
| مهارات رسمية ⭐ | **318** |
| مكرّرات محذوفة 🧹 | **50** |
| إجمالي المهارات على skills.sh | **9,730** |
| آخر تحديث | **2026-09-09** |

## 🆕 أحدث الإضافات

- **remotion-render** — `remotion-dev/skills` (75,276 تثبيت)
- **convex-auth** — `get-convex/agent-skills` (18,780 تثبيت)
- **convex-expert** — `get-convex/agent-skills` (18,749 تثبيت)
- **convex-docs** — `get-convex/agent-skills` (18,694 تثبيت)
- **convex-migrate** — `get-convex/agent-skills` (18,691 تثبيت)
- **convex-optimize** — `get-convex/agent-skills` (18,678 تثبيت)
- **convex-authz** — `get-convex/agent-skills` (18,669 تثبيت)
- **convex-reviewer** — `get-convex/agent-skills` (18,667 تثبيت)
- **convex-design** — `get-convex/agent-skills` (18,656 تثبيت)

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
