#!/usr/bin/env python3
"""
يبني أرشيف مهارات الوكلاء من skills.sh.

المخرجات:
  abbas-skills.md   الأرشيف الكامل
  README.md         صفحة المستودع
  data/skills.json  لقطة البيانات (تُستخدم لرصد التغيّرات)
  CHANGELOG.md      سجل المهارات الجديدة والخارجة من القائمة
"""
import datetime
import html
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETAILED = int(os.environ.get('DETAILED_COUNT', 500))
INDEXED = int(os.environ.get('INDEX_COUNT', 600))
BASE = 'https://www.skills.sh'
UA = 'Mozilla/5.0 (compatible; abbas-skills-archiver/1.0; +https://github.com/abbas92iraq/abbas-skills)'

S = requests.Session()
S.headers.update({'User-Agent': UA})


# ------------------------------------------------------------------ الجلب

def get(url, tries=4):
    for i in range(tries):
        try:
            r = S.get(url, timeout=45)
            if r.status_code == 200:
                return r.text
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(2 ** i)
    return None


def leaderboard():
    """أعلى المهارات مع عدد التثبيتات والاتجاه الأسبوعي، من صفحة الموقع الرئيسية."""
    page = get(BASE + '/')
    if not page:
        sys.exit('fatal: could not fetch the skills.sh homepage')
    chunks = []
    for raw in re.findall(r'self\.__next_f\.push\((\[.*?\])\)</script>', page, flags=re.S):
        try:
            arr = json.loads(raw)
        except ValueError:
            continue
        if len(arr) > 1 and isinstance(arr[1], str):
            chunks.append(arr[1])
    flight = ''.join(chunks)

    i = flight.find('"initialSkills"')
    if i < 0:
        sys.exit('fatal: leaderboard payload not found — the site layout may have changed')
    start = flight.index('[', i)
    depth = 0
    for j in range(start, len(flight)):
        if flight[j] == '[':
            depth += 1
        elif flight[j] == ']':
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    else:
        sys.exit('fatal: malformed leaderboard payload')
    skills = json.loads(flight[start:end])

    m = re.search(r'"totalSkills":(\d+)', flight)
    total = int(m.group(1)) if m else 0
    return skills, total


def fetch_page(sk):
    for url in ('%s/%s/%s' % (BASE, sk['source'], sk['skillId']),
                '%s/site/%s/%s' % (BASE, sk['source'], sk['skillId'])):
        body = get(url)
        if body and 'npx skills add' in body:
            return sk, body, url
    return sk, None, '%s/%s/%s' % (BASE, sk['source'], sk['skillId'])


# ------------------------------------------------------------------ التحليل

def text_of(x):
    x = re.sub(r'<script.*?</script>', '', x, flags=re.S)
    x = re.sub(r'<style.*?</style>', '', x, flags=re.S)
    x = re.sub(r'<li[^>]*>', '\n\x01', x)
    x = re.sub(r'</(p|div|h[1-6]|li|tr|pre)>', '\n', x)
    x = re.sub(r'<[^>]+>', '', x)
    return re.sub(r'[ \t]+', ' ', html.unescape(x)).strip()


def slice_between(s, a, b):
    i = s.find(a)
    if i < 0:
        return ''
    j = s.find(b, i + len(a))
    if j <= i:
        return ''
    return re.sub(r'^[^><]*>', '', s[i + len(a):j], count=1)


def clean(t):
    return re.sub(r'\s+', ' ', t or '').strip()


def parse(sk, s, page_url):
    o = dict(sk)
    o['page_url'] = page_url
    o['id'] = '%s/%s' % (sk['source'], sk['skillId'])
    o['install'] = 'npx skills add https://github.com/%s --skill %s' % (sk['source'], sk['skillId'])
    o['repo'] = sk['source']
    o.update(headline='', bullets=[], meta='', installs_display='', stars='', first_seen='', audits=[])
    if not s:
        return o

    m = re.search(r'npx skills add [^<"\\]+', s)
    if m:
        o['install'] = clean(m.group(0))
    m = re.search(r'<meta name="description" content="(.*?)"', s)
    if m:
        o['meta'] = clean(html.unescape(m.group(1)))

    headline, bullets = '', []
    if '>Summary<' in s:
        for line in text_of(slice_between(s, '>Summary<', '>SKILL.md<')).split('\n'):
            line = line.strip()
            if not line:
                continue
            if line.startswith('\x01'):
                b = clean(line[1:])
                if b:
                    bullets.append(b)
            elif not headline and len(line) > 15:
                headline = clean(line)
    if not headline:
        body = re.sub(r'Show more\s*$', '', text_of(slice_between(s, '>SKILL.md<', '>Installs<'))).strip()
        paras = [clean(p.lstrip('\x01')) for p in body.split('\n') if len(clean(p)) > 25]
        if paras:
            headline = paras[0][:400]
            bullets = [p[:300] for p in paras[1:4]]
    o['headline'] = headline or o['meta']
    o['bullets'] = bullets[:5]

    stats = [l.strip().lstrip('\x01').strip()
             for l in text_of(slice_between(s, '>Installs<', 'Browse')).split('\n')]
    stats = [l for l in stats if l]

    def after(label):
        for i, l in enumerate(stats):
            if l == label and i + 1 < len(stats):
                return stats[i + 1]
        return ''

    if stats and re.match(r'^[\d.,]+[KMB]?$', stats[0]):
        o['installs_display'] = stats[0]
    o['repo'] = after('Repository') or sk['source']
    o['stars'] = after('GitHub Stars')
    o['first_seen'] = after('First Seen')
    if 'Security Audits' in stats:
        for l in stats[stats.index('Security Audits') + 1:]:
            m2 = re.match(r'^(.*?)(Pass|Fail|Warn|Pending)$', l)
            if not m2:
                break
            o['audits'].append('%s: %s' % (m2.group(1).strip(), m2.group(2)))
    return o


# ------------------------------------------------------------------ التوليد

def num(n):
    return '{:,}'.format(n)


def esc(t):
    return clean((t or '').replace('|', '\\|'))


def trend(w):
    if not w or len(w) < 2 or not w[0]:
        return ''
    pct = (w[-1] - w[0]) / w[0] * 100
    arrow = '📈' if pct > 5 else ('📉' if pct < -5 else '➖')
    return '%s %+.0f%% (%s ← %s)' % (arrow, pct, num(w[-1]), num(w[0]))


def build_markdown(rows, index_rows, total_site, date):
    L = []
    w = L.append
    w('# abbas skills — أرشيف مهارات الوكلاء (Agent Skills Archive)')
    w('')
    w('> أرشيف منظّم لمهارات الوكلاء (Agent Skills) من موقع [skills.sh](https://www.skills.sh/)،')
    w('> جاهز للاستخدام كمرجع داخل المحادثات مع Claude Code وبقية وكلاء البرمجة.')
    w('>')
    w('> 🔄 **يُحدَّث تلقائيًا كل يوم** عبر GitHub Actions.')
    w('')
    w('| | |')
    w('|---|---|')
    w('| **آخر تحديث** | %s |' % date)
    w('| **المصدر** | https://www.skills.sh/ |')
    w('| **إجمالي المهارات على الموقع** | %s مهارة |' % num(total_site))
    w('| **المهارات الموثّقة بالتفصيل هنا** | %s مهارة (الأعلى تثبيتًا) |' % num(len(rows)))
    w('| **المهارات في الفهرس السريع** | %s مهارة |' % num(len(index_rows)))
    w('| **إجمالي التثبيتات للمهارات المؤرشفة** | %s تثبيت |' % num(sum(r['installs'] for r in index_rows)))
    w('')
    w('📋 المهارات الجديدة والخارجة من القائمة مسجّلة في [`CHANGELOG.md`](./CHANGELOG.md)')
    w('')
    w('---')
    w('')
    w('## 📖 كيف أستخدم هذا الملف؟')
    w('')
    w('**١. لتثبيت أي مهارة** — انسخ أمر التثبيت الموجود تحت كل مهارة ونفّذه في مجلد مشروعك:')
    w('')
    w('```bash')
    w('npx skills add https://github.com/anthropics/skills --skill pdf')
    w('```')
    w('')
    w('**٢. لتثبيت مستودع كامل** (كل المهارات التي بداخله):')
    w('')
    w('```bash')
    w('npx skills add vercel-labs/skills')
    w('```')
    w('')
    w('**٣. داخل المحادثة مع الوكيل** — ارفع هذا الملف أو أشر إليه، ثم اطلب مثلًا:')
    w('> «ابحث في `abbas-skills.md` عن مهارة مناسبة لمراجعة الكود، وثبّتها.»')
    w('')
    w('**٤. الأوامر المفيدة:**')
    w('')
    w('| الأمر | الوظيفة |')
    w('|---|---|')
    w('| `npx skills add <owner/repo>` | تثبيت كل مهارات المستودع |')
    w('| `npx skills add <url> --skill <name>` | تثبيت مهارة واحدة محددة |')
    w('| `npx skills list` | عرض المهارات المثبّتة |')
    w('| `npx skills remove <name>` | إزالة مهارة |')
    w('')
    w('> المهارات تعمل مع: Claude Code · Cursor · Codex · GitHub Copilot · Windsurf · Gemini · Cline · AMP · Zed · وغيرها.')
    w('')
    w('---')
    w('')
    w('## 🧭 دليل قراءة البطاقات')
    w('')
    w('| الحقل | المعنى |')
    w('|---|---|')
    w('| **التثبيتات** | إجمالي مرات التثبيت منذ إدراج المهارة (مؤشر الشعبية) |')
    w('| **الاتجاه** | تغيّر التثبيتات الأسبوعية خلال آخر ٨ أسابيع (مؤشر النشاط الحالي) |')
    w('| **نجوم GitHub** | نجوم المستودع المصدر |')
    w('| **أول ظهور** | تاريخ إدراج المهارة في skills.sh |')
    w('| **الفحص الأمني** | نتائج تدقيق `Gen Agent Trust Hub` / `Socket` / `Snyk` |')
    w('| ⭐ | مهارة رسمية (Official) من الجهة المطوِّرة للتقنية نفسها |')
    w('| 🆕 | مهارة دخلت القائمة خلال آخر تحديث |')
    w('')
    w('---')
    w('')

    own = {}
    for r in index_rows:
        d = own.setdefault(r['source'].split('/')[0], {'n': 0, 'i': 0})
        d['n'] += 1
        d['i'] += r['installs']
    w('## 🏢 أبرز الجهات المصدِّرة للمهارات')
    w('')
    w('| # | الجهة | عدد المهارات | إجمالي التثبيتات |')
    w('|---:|---|---:|---:|')
    for i, (o, d) in enumerate(sorted(own.items(), key=lambda kv: -kv[1]['i'])[:30], 1):
        w('| %d | `%s` | %d | %s |' % (i, o, d['n'], num(d['i'])))
    w('')
    w('---')
    w('')

    w('## ⚡ الفهرس السريع (أعلى %s مهارة)' % num(len(index_rows)))
    w('')
    w('<details>')
    w('<summary>اضغط لفتح الجدول الكامل</summary>')
    w('')
    w('| # | المهارة | المصدر | التثبيتات | التفاصيل |')
    w('|---:|---|---|---:|---|')
    for i, r in enumerate(index_rows, 1):
        badges = (' ⭐' if r.get('isOfficial') else '') + (' 🆕' if r.get('is_new') else '')
        link = ('[↓](#skill-%d)' % i) if i <= len(rows) else \
               ('[🔗](%s/%s/%s)' % (BASE, r['source'], r['skillId']))
        w('| %d | **%s**%s | `%s` | %s | %s |' % (i, esc(r['name']), badges, r['source'], num(r['installs']), link))
    w('')
    w('</details>')
    w('')
    w('---')
    w('')

    w('## 📚 التفاصيل الكاملة — أعلى %s مهارة' % num(len(rows)))
    w('')
    for i, r in enumerate(rows, 1):
        badges = (' ⭐' if r.get('isOfficial') else '') + (' 🆕' if r.get('is_new') else '')
        w('<a id="skill-%d"></a>' % i)
        w('')
        w('### %d. %s%s' % (i, r['name'], badges))
        w('')
        w('**الوصف:** %s' % (esc(r['headline']) or esc(r['meta']) or '_لا يوجد وصف منشور على الموقع._'))
        w('')
        if r['bullets']:
            w('**أبرز القدرات:**')
            w('')
            for b in r['bullets']:
                w('- %s' % esc(b))
            w('')
        w('**التثبيت:**')
        w('')
        w('```bash')
        w(r['install'])
        w('```')
        w('')
        perf = ['**التثبيتات:** %s' % num(r['installs'])]
        t = trend(r.get('weeklyInstalls'))
        if t:
            perf.append('**الاتجاه:** %s' % t)
        if r.get('stars'):
            perf.append('**نجوم GitHub:** %s' % r['stars'])
        if r.get('first_seen'):
            perf.append('**أول ظهور:** %s' % r['first_seen'])
        w('**الأداء:** ' + ' · '.join(perf))
        w('')
        if r.get('audits'):
            w('**الفحص الأمني:** ' + ' · '.join(r['audits']))
            w('')
        w('**المصدر:** [`%s`](https://github.com/%s) · **الصفحة:** [skills.sh](%s)' %
          (r['repo'], r['source'], r['page_url']))
        w('')
        w('---')
        w('')

    w('## ℹ️ ملاحظات')
    w('')
    w('- الأرقام (التثبيتات / النجوم / الاتجاه) لقطة بتاريخ **%s** وتتغيّر باستمرار.' % date)
    w('- الترتيب حسب إجمالي التثبيتات (all-time) كما يعرضه skills.sh.')
    w('- «الاتجاه» يقارن التثبيتات في الأسبوع الأخير بالأسبوع الأول من آخر ٨ أسابيع.')
    w('- نتائج الفحص الأمني منقولة كما هي من الموقع، ولا تُغني عن مراجعة محتوى المهارة قبل تثبيتها.')
    w('- بقية المهارات (إجمالي %s على الموقع) يمكن تصفّحها من https://www.skills.sh/' % num(total_site))
    w('')
    return '\n'.join(L)


def build_readme(rows, index_rows, total_site, date, new_names):
    official = sum(1 for r in rows if r.get('isOfficial'))
    L = []
    w = L.append
    w('# abbas skills')
    w('')
    w('أرشيف منظّم لمهارات الوكلاء (**Agent Skills**) المأخوذة من [skills.sh](https://www.skills.sh/)، '
      'لاستخدامها كمرجع داخل المحادثات مع Claude Code وبقية وكلاء البرمجة.')
    w('')
    w('🔄 **يُحدَّث تلقائيًا كل يوم** الساعة ٦ صباحًا بتوقيت بغداد عبر GitHub Actions.')
    w('')
    w('## 📄 الملف الرئيسي')
    w('')
    w('### 👉 [`abbas-skills.md`](./abbas-skills.md)')
    w('')
    w('| المحتوى | العدد |')
    w('|---|---:|')
    w('| مهارات موثّقة بالتفصيل الكامل | **%s** |' % num(len(rows)))
    w('| مهارات في الفهرس السريع | **%s** |' % num(len(index_rows)))
    w('| منها مهارات رسمية (Official) | **%s** |' % num(official))
    w('| إجمالي المهارات المتاحة على skills.sh | **%s** |' % num(total_site))
    w('| آخر تحديث | **%s** |' % date)
    w('')
    if new_names:
        w('## 🆕 أحدث المهارات الداخلة للقائمة')
        w('')
        for n in new_names[:10]:
            w('- `%s`' % n)
        w('')
        w('السجل الكامل في [`CHANGELOG.md`](./CHANGELOG.md).')
        w('')
    w('## ✅ ما الذي يحتويه كل سجل؟')
    w('')
    w('- **الاسم** والمستودع المصدر')
    w('- **أمر التثبيت** الجاهز للنسخ (`npx skills add ...`)')
    w('- **الوصف** وأبرز القدرات')
    w('- **الأداء**: عدد التثبيتات · اتجاه آخر ٨ أسابيع · نجوم GitHub · تاريخ أول ظهور')
    w('- **نتائج الفحص الأمني** (Gen Agent Trust Hub · Socket · Snyk)')
    w('- **روابط** صفحة المهارة والمستودع')
    w('')
    w('## 🚀 الاستخدام السريع')
    w('')
    w('```bash')
    w('# تثبيت مهارة واحدة')
    w('npx skills add https://github.com/anthropics/skills --skill pdf')
    w('')
    w('# تثبيت كل مهارات مستودع')
    w('npx skills add vercel-labs/skills')
    w('```')
    w('')
    w('داخل المحادثة مع الوكيل:')
    w('')
    w('> «راجع `abbas-skills.md` واختر لي مهارة مناسبة لـ ... ثم ثبّتها.»')
    w('')
    w('## ⚙️ آلية التحديث')
    w('')
    w('| الملف | الوظيفة |')
    w('|---|---|')
    w('| [`scripts/build_archive.py`](./scripts/build_archive.py) | يسحب البيانات من skills.sh ويعيد بناء الأرشيف |')
    w('| [`.github/workflows/daily-update.yml`](./.github/workflows/daily-update.yml) | يشغّل السكربت يوميًا ويرفع التغييرات |')
    w('| [`data/skills.json`](./data/skills.json) | لقطة البيانات، تُستخدم لرصد الداخل والخارج من القائمة |')
    w('| [`CHANGELOG.md`](./CHANGELOG.md) | سجل التغييرات اليومي |')
    w('')
    w('للتشغيل اليدوي: تبويب **Actions** ← **Daily skills archive update** ← **Run workflow**.')
    w('')
    w('---')
    w('')
    w('**المصدر:** https://www.skills.sh/')
    return '\n'.join(L) + '\n'


def build_changelog(date, new_rows, gone, prev_exists, old_path, total):
    entry = ['## %s' % date, '']
    if not prev_exists:
        entry.append('- 📦 أول أرشفة: %s مهارة.' % num(total))
        entry.append('')
    else:
        if new_rows:
            entry.append('### 🆕 دخلت قائمة أفضل %s (%d)' % (DETAILED, len(new_rows)))
            entry.append('')
            entry.append('| المهارة | المصدر | التثبيتات | الوصف |')
            entry.append('|---|---|---:|---|')
            for r in new_rows:
                d = esc(r.get('headline') or r.get('meta') or '')
                entry.append('| **%s** | `%s` | %s | %s |' % (esc(r['name']), r['source'], num(r['installs']), d[:140]))
            entry.append('')
        if gone:
            entry.append('### 📤 خرجت من القائمة (%d)' % len(gone))
            entry.append('')
            for g in gone:
                entry.append('- `%s`' % g)
            entry.append('')
        if not new_rows and not gone:
            entry.append('- ➖ لا تغيير في تشكيلة أفضل %s؛ حُدِّثت الأرقام فقط.' % DETAILED)
            entry.append('')

    old = ''
    if os.path.exists(old_path):
        old = open(old_path, encoding='utf-8').read()
        old = re.sub(r'^# سجل التغييرات\n+', '', old)
        old = re.sub(r'^سجل .*?\n+', '', old, flags=re.M)
    head = '# سجل التغييرات\n\nسجل يومي بالمهارات الداخلة إلى قائمة أفضل %s والخارجة منها.\n\n' % DETAILED
    body = '\n'.join(entry).rstrip() + '\n'
    # لا تكرّر مدخل اليوم نفسه إن أُعيد التشغيل
    old = re.sub(r'^## %s\n.*?(?=^## |\Z)' % re.escape(date), '', old, flags=re.S | re.M)
    return head + body + '\n' + old.strip() + ('\n' if old.strip() else '')


# ------------------------------------------------------------------ main

def main():
    date = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    print('building archive for', date, flush=True)

    board, total_site = leaderboard()
    print('leaderboard entries:', len(board), '| site total:', total_site, flush=True)
    if len(board) < DETAILED:
        sys.exit('fatal: leaderboard returned only %d entries, need %d' % (len(board), DETAILED))

    index_rows = board[:INDEXED]
    targets = board[:DETAILED]

    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for n, (sk, body, url) in enumerate(ex.map(fetch_page, targets), 1):
            results.append(parse(sk, body, url))
            if n % 100 == 0:
                print('  parsed', n, flush=True)

    snap_path = os.path.join(ROOT, 'data', 'skills.json')
    prev = {}
    prev_exists = os.path.exists(snap_path)
    if prev_exists:
        try:
            old = json.load(open(snap_path, encoding='utf-8'))
            prev = {r['id']: r for r in old.get('skills', [])}
        except (ValueError, KeyError):
            prev_exists = False

    # استرجاع بيانات الأمس للصفحات التي فشل جلبها اليوم
    recovered = 0
    for r in results:
        if not r['headline'] and r['id'] in prev:
            p = prev[r['id']]
            for k in ('headline', 'bullets', 'meta', 'stars', 'first_seen', 'audits', 'install'):
                if p.get(k):
                    r[k] = p[k]
            recovered += 1
    if recovered:
        print('recovered %d skill(s) from the previous snapshot' % recovered, flush=True)

    new_rows = [r for r in results if prev_exists and r['id'] not in prev]
    now_ids = {r['id'] for r in results}
    gone = sorted(i for i in prev if i not in now_ids) if prev_exists else []
    for r in new_rows:
        r['is_new'] = True
    new_ids = {r['id'] for r in new_rows}
    for r in index_rows:
        r['is_new'] = ('%s/%s' % (r['source'], r['skillId'])) in new_ids
    print('new: %d | gone: %d' % (len(new_rows), len(gone)), flush=True)

    md = build_markdown(results, index_rows, total_site, date)
    open(os.path.join(ROOT, 'abbas-skills.md'), 'w', encoding='utf-8').write(md)
    open(os.path.join(ROOT, 'README.md'), 'w', encoding='utf-8').write(
        build_readme(results, index_rows, total_site, date, [r['name'] for r in new_rows]))
    open(os.path.join(ROOT, 'CHANGELOG.md'), 'w', encoding='utf-8').write(
        build_changelog(date, new_rows, gone, prev_exists, os.path.join(ROOT, 'CHANGELOG.md'), len(results)))
    json.dump({'generated_at': date, 'total_site_skills': total_site, 'skills': results},
              open(snap_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    missing = sum(1 for r in results if not r['headline'])
    print('done — %d skills, %d without a description' % (len(results), missing), flush=True)

    out = os.environ.get('GITHUB_OUTPUT')
    if out:
        with open(out, 'a', encoding='utf-8') as fh:
            fh.write('new_count=%d\n' % len(new_rows))
            fh.write('gone_count=%d\n' % len(gone))
            fh.write('total_site=%d\n' % total_site)


if __name__ == '__main__':
    main()
