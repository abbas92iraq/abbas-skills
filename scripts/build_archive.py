#!/usr/bin/env python3
"""
يبني أرشيف مهارات الوكلاء من skills.sh.

مبادئ:
  • تراكمي   — المهارة التي دخلت الأرشيف لا تخرج منه أبدًا بسبب تراجع ترتيبها.
  • بلا تكرار — المهارات التي تؤدي العمل نفسه تُدمج، ويبقى الأقوى فقط.

المخرجات:
  abbas-skills.md   الأرشيف الكامل بالتفاصيل
  INDEX.md          فهرس مضغوط سطر لكل مهارة (للبحث السريع)
  README.md         صفحة المستودع
  CHANGELOG.md      سجل يومي بالجديد
  DUPLICATES.md     تقرير التكرارات المحذوفة والمعلّقة للمراجعة
  data/skills.json  لقطة البيانات
"""
import datetime
import difflib
import html
import json
import os
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOP_N = int(os.environ.get('TOP_N', 1000))
BASE = 'https://www.skills.sh'
PAGE_SIZE = 200
UA = 'Mozilla/5.0 (compatible; abbas-skills-archiver/2.0; +https://github.com/abbas92iraq/abbas-skills)'

S = requests.Session()
S.headers.update({'User-Agent': UA})


# ------------------------------------------------------------------ الجلب

def get(url, tries=4, as_json=False):
    for i in range(tries):
        try:
            r = S.get(url, timeout=45)
            if r.status_code == 200:
                return r.json() if as_json else r.text
            if r.status_code == 404:
                return None
        except (requests.RequestException, ValueError):
            pass
        time.sleep(2 ** i)
    return None


def leaderboard(limit):
    """أعلى المهارات مرتّبة حسب التثبيتات: أول 600 من الصفحة الرئيسية، والباقي من API الصفحات."""
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
    end = -1
    for j in range(start, len(flight)):
        if flight[j] == '[':
            depth += 1
        elif flight[j] == ']':
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    if end < 0:
        sys.exit('fatal: malformed leaderboard payload')
    board = json.loads(flight[start:end])

    m = re.search(r'"totalSkills":(\d+)', flight)
    total_site = int(m.group(1)) if m else 0

    page_no = len(board) // PAGE_SIZE
    while len(board) < limit:
        data = get('%s/api/skills/all-time/%d' % (BASE, page_no), as_json=True)
        if not data or not data.get('skills'):
            print('warning: pagination stopped at page %d (%d entries)' % (page_no, len(board)), flush=True)
            break
        board.extend(data['skills'])
        if not data.get('hasMore'):
            break
        page_no += 1

    seen, uniq = set(), []
    for r in board:
        key = '%s/%s' % (r['source'], r['skillId'])
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    return uniq[:limit], total_site


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
    o['id'] = '%s/%s' % (sk['source'], sk['skillId'])
    o['page_url'] = page_url
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


# ------------------------------------------------------------------ كشف التكرار

STOP = set('the a an and or of to for with in on your you use using when this that is are be it its '
           'as by from at into via not no if then can will user users agent agents skill skills'.split())


def norm_name(n):
    n = re.sub(r'[^a-z0-9]+', ' ', (n or '').lower())
    n = re.sub(r'\b(v?\d+(\.\d+)*)\b', ' ', n)
    return ' '.join(n.split())


def desc_tokens(r):
    t = ' '.join([r.get('headline') or '', ' '.join(r.get('bullets') or []), r.get('meta') or ''])
    return {w for w in re.findall(r'[a-z][a-z0-9+-]{2,}', t.lower()) if w not in STOP}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def headline_ratio(a, b):
    ha = (a.get('headline') or a.get('meta') or '').lower()
    hb = (b.get('headline') or b.get('meta') or '').lower()
    if len(ha) < 25 or len(hb) < 25:
        return 0.0
    return difflib.SequenceMatcher(None, ha, hb).ratio()


def is_stub(r):
    d = (r.get('headline') or '') + ' '.join(r.get('bullets') or [])
    return len(d.strip()) < 120 or 'npx skills add' in d


def stars_num(r):
    m = re.match(r'^([\d.]+)\s*([KMB])?$', (r.get('stars') or '').strip())
    if not m:
        return 0
    return float(m.group(1)) * {'K': 1e3, 'M': 1e6, 'B': 1e9}.get(m.group(2) or '', 1)


def pick_winner(members):
    """يستبعد النسخ الاختصارية/الوكيلة (مثل: 'Install the belt CLI skill: ...')
    من السباق ما دام هناك نسخة تحمل محتوى حقيقيًا، بصرف النظر عن عدد تثبيتاتها —
    قد تتضخم تثبيتات الوكيل الاختصاري لأسباب لا علاقة لها بجودة الشرح الفعلي."""
    real = [m for m in members if not is_stub(m)]
    pool = real if real else members
    return max(pool, key=quality)


def quality(r):
    """كلما زاد، كانت المهارة أجدر بالبقاء: التثبيتات ثم الفحص الأمني ثم النجوم ثم الأقدمية."""
    passes = sum(1 for a in r.get('audits') or [] if a.endswith('Pass'))
    try:
        seen = datetime.datetime.strptime(r.get('first_seen') or '', '%b %d, %Y').toordinal()
    except ValueError:
        seen = 10 ** 7
    return (r.get('installs', 0), passes, stars_num(r), -seen)


def find_duplicates(rows):
    """
    يجمع المهارات ذات العمل نفسه.

    يُحذف تلقائيًا فقط عند ثقة عالية:
      • اسم مركّب متطابق (كلمتان فأكثر) عبر مستودعين مختلفين — مثل lark-doc أو ai-video-generation
      • أو تطابق وصف ≥ 45%
      • أو كون إحدى النسخ مجرد وكيل/اختصار لأخرى
    الأسماء المفردة العامة (prototype، review) تُعلَّق للمراجعة ولا تُحذف،
    لأن تشابه الاسم وحده لا يعني تشابه العمل. ولا يُقارَن أبدًا بين مهارتين من المستودع نفسه.
    """
    for r in rows:
        r['_nn'] = norm_name(r['name'])
        r['_tk'] = desc_tokens(r)

    groups = defaultdict(list)
    for r in rows:
        groups[r['_nn']].append(r)

    removed, flagged = {}, []
    for nn, g in groups.items():
        if len(g) < 2 or len({x['source'] for x in g}) < 2:
            continue
        best = max((jaccard(a['_tk'], b['_tk']) for i, a in enumerate(g) for b in g[i + 1:]), default=0.0)
        hbest = max((headline_ratio(a, b) for i, a in enumerate(g) for b in g[i + 1:]), default=0.0)
        ntok = len(nn.split())
        if ntok >= 2:
            reason = 'اسم مركّب متطابق (%d كلمات) عبر مصادر مختلفة' % ntok
        elif best >= 0.45:
            reason = 'وصف متطابق بنسبة %.0f%%' % (best * 100)
        elif hbest >= 0.60:
            reason = 'نص الوصف شبه حرفي (%.0f%%)' % (hbest * 100)
        elif any(is_stub(x) for x in g):
            reason = 'إحدى النسخ مجرّد اختصار يشير إلى الأخرى'
        else:
            flagged.append({'key': nn, 'similarity': round(max(best, hbest), 2),
                            'members': [{'id': x['id'], 'installs': x['installs'],
                                         'headline': x.get('headline', '')[:160]} for x in
                                        sorted(g, key=quality, reverse=True)]})
            continue
        winner = pick_winner(g)
        for loser in g:
            if loser is winner:
                continue
            removed[loser['id']] = {'id': loser['id'], 'name': loser['name'], 'source': loser['source'],
                                    'installs': loser['installs'], 'reason': reason,
                                    'kept': winner['id'], 'kept_installs': winner['installs'],
                                    'headline': (loser.get('headline') or '')[:200]}

    # تطابق الأوصاف عبر أسماء مختلفة (نسخ مُعاد تسميتها)
    ids = [r for r in rows if r['id'] not in removed]
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if a['source'] == b['source'] or a['id'] in removed or b['id'] in removed:
                continue
            if not a['_tk'] or not b['_tk']:
                continue
            if jaccard(a['_tk'], b['_tk']) >= 0.75 and \
               difflib.SequenceMatcher(None, a['_nn'], b['_nn']).ratio() >= 0.55:
                w = pick_winner([a, b])
                l = b if w is a else a
                removed[l['id']] = {'id': l['id'], 'name': l['name'], 'source': l['source'],
                                    'installs': l['installs'],
                                    'reason': 'وصف شبه مطابق (%.0f%%) لمهارة أقوى' % (jaccard(a['_tk'], b['_tk']) * 100),
                                    'kept': w['id'], 'kept_installs': w['installs'],
                                    'headline': (l.get('headline') or '')[:200]}

    for r in rows:
        r.pop('_nn', None)
        r.pop('_tk', None)
    return removed, flagged


# ------------------------------------------------------------------ التوليد

def num(n):
    return '{:,}'.format(int(n))


def esc(t):
    return clean((t or '').replace('|', '\\|'))


def trend(w):
    if not w or len(w) < 2 or not w[0]:
        return ''
    pct = (w[-1] - w[0]) / w[0] * 100
    arrow = '📈' if pct > 5 else ('📉' if pct < -5 else '➖')
    return '%s %+.0f%% (%s ← %s)' % (arrow, pct, num(w[-1]), num(w[0]))


def badges(r):
    b = ''
    if r.get('isOfficial'):
        b += ' ⭐'
    if r.get('is_new'):
        b += ' 🆕'
    if not r.get('in_top'):
        b += ' 📌'
    return b


def build_archive_md(rows, total_site, date, removed, flagged, top_n):
    L = []
    w = L.append
    w('# abbas skills — أرشيف مهارات الوكلاء (Agent Skills Archive)')
    w('')
    w('> أرشيف تراكمي منظّم لمهارات الوكلاء (Agent Skills) من [skills.sh](https://www.skills.sh/)،')
    w('> جاهز للاستخدام كمرجع داخل المحادثات مع Claude Code وبقية وكلاء البرمجة.')
    w('>')
    w('> 🔄 **يُحدَّث تلقائيًا كل يوم** · ➕ **تراكمي: لا تخرج أي مهارة بسبب تراجع ترتيبها**')
    w('> · 🧹 **منقّى: المهارات المكرّرة تُدمج ويبقى الأقوى**')
    w('')
    w('| | |')
    w('|---|---|')
    w('| **آخر تحديث** | %s |' % date)
    w('| **المصدر** | https://www.skills.sh/ |')
    w('| **المهارات في هذا الأرشيف** | %s مهارة |' % num(len(rows)))
    w('| **نطاق المتابعة اليومية** | أعلى %s مهارة |' % num(top_n))
    w('| **مهارات محفوظة خارج النطاق** 📌 | %s |' % num(sum(1 for r in rows if not r.get('in_top'))))
    w('| **مكرّرات محذوفة** | %s |' % num(len(removed)))
    w('| **إجمالي المهارات على الموقع** | %s |' % num(total_site))
    w('| **إجمالي التثبيتات** | %s |' % num(sum(r['installs'] for r in rows)))
    w('')
    w('🔎 للبحث السريع: [`INDEX.md`](./INDEX.md) · '
      '📋 الجديد: [`CHANGELOG.md`](./CHANGELOG.md) · '
      '🧹 المكرّرات: [`DUPLICATES.md`](./DUPLICATES.md)')
    w('')
    w('---')
    w('')
    w('## 📖 كيف أستخدم هذا الملف؟')
    w('')
    w('**١. لتثبيت أي مهارة** — انسخ أمر التثبيت الموجود تحتها ونفّذه في مجلد مشروعك:')
    w('')
    w('```bash')
    w('npx skills add https://github.com/anthropics/skills --skill pdf')
    w('```')
    w('')
    w('**٢. لتثبيت مستودع كامل:**')
    w('')
    w('```bash')
    w('npx skills add vercel-labs/skills')
    w('```')
    w('')
    w('**٣. داخل المحادثة مع الوكيل** — الملف كبير، فالأفضل البحث فيه لا قراءته كاملًا:')
    w('')
    w('> «ابحث في `INDEX.md` عن مهارة لمراجعة الكود، ثم اقرأ تفاصيلها من `abbas-skills.md` وثبّتها.»')
    w('')
    w('**٤. الأوامر المفيدة:**')
    w('')
    w('| الأمر | الوظيفة |')
    w('|---|---|')
    w('| `npx skills add <owner/repo>` | تثبيت كل مهارات المستودع |')
    w('| `npx skills add <url> --skill <name>` | تثبيت مهارة واحدة |')
    w('| `npx skills list` | عرض المهارات المثبّتة |')
    w('| `npx skills remove <name>` | إزالة مهارة |')
    w('')
    w('> تعمل مع: Claude Code · Cursor · Codex · GitHub Copilot · Windsurf · Gemini · Cline · AMP · Zed · وغيرها.')
    w('')
    w('---')
    w('')
    w('## 🧭 دليل قراءة البطاقات')
    w('')
    w('| الرمز/الحقل | المعنى |')
    w('|---|---|')
    w('| ⭐ | مهارة رسمية من الجهة المطوِّرة للتقنية نفسها |')
    w('| 🆕 | أُضيفت في آخر تحديث |')
    w('| 📌 | محفوظة في الأرشيف رغم خروجها من نطاق المتابعة اليومي — بياناتها قد تكون أقدم |')
    w('| **التثبيتات** | إجمالي مرات التثبيت (مؤشر الشعبية) |')
    w('| **الاتجاه** | تغيّر التثبيتات الأسبوعية خلال آخر ٨ أسابيع |')
    w('| **نجوم GitHub** | نجوم المستودع المصدر |')
    w('| **أول ظهور** | تاريخ إدراج المهارة في skills.sh |')
    w('| **الفحص الأمني** | تدقيق `Gen Agent Trust Hub` / `Socket` / `Snyk` |')
    w('')
    w('---')
    w('')

    own = defaultdict(lambda: {'n': 0, 'i': 0})
    for r in rows:
        d = own[r['source'].split('/')[0]]
        d['n'] += 1
        d['i'] += r['installs']
    w('## 🏢 أبرز الجهات المصدِّرة')
    w('')
    w('| # | الجهة | عدد المهارات | إجمالي التثبيتات |')
    w('|---:|---|---:|---:|')
    for i, (o, d) in enumerate(sorted(own.items(), key=lambda kv: -kv[1]['i'])[:30], 1):
        w('| %d | `%s` | %d | %s |' % (i, o, d['n'], num(d['i'])))
    w('')
    w('---')
    w('')

    w('## ⚡ الفهرس السريع')
    w('')
    w('<details>')
    w('<summary>اضغط لفتح جدول المهارات الـ%s</summary>' % num(len(rows)))
    w('')
    w('| # | المهارة | المصدر | التثبيتات | التفاصيل |')
    w('|---:|---|---|---:|---|')
    for i, r in enumerate(rows, 1):
        w('| %d | **%s**%s | `%s` | %s | [↓](#skill-%d) |' %
          (i, esc(r['name']), badges(r), r['source'], num(r['installs']), i))
    w('')
    w('</details>')
    w('')
    w('---')
    w('')

    w('## 📚 التفاصيل الكاملة')
    w('')
    for i, r in enumerate(rows, 1):
        w('<a id="skill-%d"></a>' % i)
        w('')
        w('### %d. %s%s' % (i, r['name'], badges(r)))
        w('')
        w('**الوصف:** %s' % (esc(r.get('headline')) or esc(r.get('meta')) or '_لا يوجد وصف منشور._'))
        w('')
        if r.get('bullets'):
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
        if not r.get('in_top'):
            w('> 📌 خارج نطاق المتابعة اليومي حاليًا — آخر تحديث لبياناتها: %s' % r.get('last_updated', '—'))
            w('')
        w('**المصدر:** [`%s`](https://github.com/%s) · **الصفحة:** [skills.sh](%s)' %
          (r.get('repo') or r['source'], r['source'], r['page_url']))
        w('')
        w('---')
        w('')

    w('## ℹ️ ملاحظات')
    w('')
    w('- الأرقام لقطة بتاريخ **%s** وتتغيّر باستمرار.' % date)
    w('- الترتيب حسب إجمالي التثبيتات (all-time).')
    w('- الأرشيف **تراكمي**: المهارة التي دخلت لا تخرج بسبب تراجع ترتيبها، بل تُوسم بـ 📌.')
    w('- المهارات المكرّرة (نفس العمل من مصادر مختلفة) تُحذف ويبقى الأقوى — التفاصيل في '
      '[`DUPLICATES.md`](./DUPLICATES.md)%s.' %
      ('، مع %d حالة معلّقة للمراجعة اليدوية' % len(flagged) if flagged else ''))
    w('- نتائج الفحص الأمني منقولة كما هي، ولا تُغني عن مراجعة المهارة قبل تثبيتها.')
    w('')
    return '\n'.join(L)


def build_index_md(rows, date):
    L = ['# فهرس المهارات (مضغوط)', '',
         'سطر واحد لكل مهارة — للبحث السريع. التفاصيل الكاملة في [`abbas-skills.md`](./abbas-skills.md).', '',
         '**آخر تحديث:** %s · **العدد:** %s مهارة' % (date, num(len(rows))), '',
         '> للوكلاء: ابحث هنا أولًا بكلمة مفتاحية، ثم اقرأ البطاقة الكاملة من `abbas-skills.md`.', '', '---', '']
    for i, r in enumerate(rows, 1):
        d = esc(r.get('headline') or r.get('meta') or '')[:150]
        L.append('%d. **%s** — `%s` · %s تثبيت%s' %
                 (i, esc(r['name']), r['id'], num(r['installs']), ' ⭐' if r.get('isOfficial') else ''))
        L.append('   %s' % (d or '—'))
        L.append('   `%s`' % r['install'])
        L.append('')
    return '\n'.join(L)


def build_duplicates_md(removed, flagged, date):
    L = ['# تقرير المهارات المكرّرة', '',
         'يُعاد حسابه في كل تحديث. المهارات التي تؤدي **العمل نفسه** من مصادر مختلفة تُدمج، ويبقى الأقوى.', '',
         '**آخر تحديث:** %s' % date, '', '## 📐 قاعدة الترجيح', '',
         'يبقى الأعلى في: **التثبيتات** ← ثم **نتائج الفحص الأمني** ← ثم **نجوم GitHub** ← ثم **الأقدمية**.', '',
         'لا يُقارَن أبدًا بين مهارتين من المستودع نفسه (المطوّر يشحنهما عمدًا كمهارتين مختلفتين).', '',
         '---', '', '## 🧹 محذوفة تلقائيًا (%d)' % len(removed), '']
    if removed:
        L += ['| المحذوفة | التثبيتات | أُبقيت بدلًا منها | تثبيتاتها | السبب |', '|---|---:|---|---:|---|']
        for r in sorted(removed.values(), key=lambda x: -x['kept_installs']):
            L.append('| `%s` | %s | `%s` | %s | %s |' %
                     (r['id'], num(r['installs']), r['kept'], num(r['kept_installs']), r['reason']))
    else:
        L.append('_لا توجد._')
    L += ['', '---', '', '## ⚠️ معلّقة للمراجعة اليدوية (%d)' % len(flagged), '',
          'تحمل الاسم نفسه لكن الأوصاف مختلفة — تُركت جميعها في الأرشيف تجنّبًا لحذف مهارة مفيدة بالخطأ.', '']
    if flagged:
        for f in flagged:
            L.append('### `%s` — تشابه الوصف %.0f%%' % (f['key'], f['similarity'] * 100))
            L.append('')
            for m in f['members']:
                L.append('- `%s` (%s تثبيت) — %s' % (m['id'], num(m['installs']), m['headline'] or '—'))
            L.append('')
    else:
        L.append('_لا توجد._')
    return '\n'.join(L) + '\n'


def build_readme(rows, total_site, date, new_rows, removed, top_n):
    official = sum(1 for r in rows if r.get('isOfficial'))
    kept = sum(1 for r in rows if not r.get('in_top'))
    L = []
    w = L.append
    w('# abbas skills')
    w('')
    w('أرشيف تراكمي منقّى لمهارات الوكلاء (**Agent Skills**) من [skills.sh](https://www.skills.sh/) — '
      'مرجع جاهز للاستخدام داخل المحادثات مع Claude Code وبقية وكلاء البرمجة.')
    w('')
    w('🔄 **تحديث تلقائي يومي** · ➕ **تراكمي** · 🧹 **بلا تكرار**')
    w('')
    w('## 📄 الملفات')
    w('')
    w('| الملف | الوظيفة |')
    w('|---|---|')
    w('| [`abbas-skills.md`](./abbas-skills.md) | الأرشيف الكامل — بطاقة تفصيلية لكل مهارة |')
    w('| [`INDEX.md`](./INDEX.md) | فهرس مضغوط سطر لكل مهارة — للبحث السريع |')
    w('| [`CHANGELOG.md`](./CHANGELOG.md) | سجل يومي بالمهارات الجديدة |')
    w('| [`DUPLICATES.md`](./DUPLICATES.md) | تقرير التكرارات المحذوفة |')
    w('| [`SKILL.md`](./SKILL.md) | يجعل المستودع نفسه مهارة قابلة للتثبيت |')
    w('')
    w('## 📊 الأرقام')
    w('')
    w('| | |')
    w('|---|---:|')
    w('| المهارات في الأرشيف | **%s** |' % num(len(rows)))
    w('| نطاق المتابعة اليومية | **أعلى %s** |' % num(top_n))
    w('| مهارات محفوظة خارج النطاق 📌 | **%s** |' % num(kept))
    w('| مهارات رسمية ⭐ | **%s** |' % num(official))
    w('| مكرّرات محذوفة 🧹 | **%s** |' % num(len(removed)))
    w('| إجمالي المهارات على skills.sh | **%s** |' % num(total_site))
    w('| آخر تحديث | **%s** |' % date)
    w('')
    if new_rows:
        w('## 🆕 أحدث الإضافات')
        w('')
        for r in new_rows[:10]:
            w('- **%s** — `%s` (%s تثبيت)' % (r['name'], r['source'], num(r['installs'])))
        w('')
        w('السجل الكامل في [`CHANGELOG.md`](./CHANGELOG.md).')
        w('')
    w('## 🤖 استخدامه كمساعد افتراضي')
    w('')
    w('**الطريقة الأولى — تثبيته كمهارة** (يجعل الوكيل يستشير الأرشيف تلقائيًا):')
    w('')
    w('```bash')
    w('npx skills add abbas92iraq/abbas-skills')
    w('```')
    w('')
    w('**الطريقة الثانية — إضافته لذاكرة Claude Code الدائمة:**')
    w('')
    w('```bash')
    w('git clone https://github.com/abbas92iraq/abbas-skills ~/abbas-skills')
    w('```')
    w('')
    w('ثم أضف هذا إلى `~/.claude/CLAUDE.md`:')
    w('')
    w('```markdown')
    w('## مرجع المهارات')
    w('عند الحاجة إلى مهارة (skill) لأي مهمة، ابحث أولًا في `~/abbas-skills/INDEX.md`،')
    w('ثم اقرأ البطاقة الكاملة من `~/abbas-skills/abbas-skills.md` ونفّذ أمر التثبيت.')
    w('لا تقرأ `abbas-skills.md` كاملًا — ابحث فيه بكلمة مفتاحية.')
    w('```')
    w('')
    w('**الطريقة الثالثة — في جلسات Claude Code على الويب:** أضف المستودع كمصدر (Source) للبيئة، '
      'فيصبح متاحًا في كل جلسة جديدة.')
    w('')
    w('## ⚙️ آلية التحديث')
    w('')
    w('يوميًا **06:00 صباحًا بتوقيت بغداد** عبر [GitHub Actions](./.github/workflows/daily-update.yml):')
    w('')
    w('1. سحب أعلى **%s** مهارة من لوحة صدارة skills.sh' % num(top_n))
    w('2. جلب صفحة كل مهارة واستخراج الوصف والأداء والفحص الأمني')
    w('3. **الدمج التراكمي** مع الأرشيف — لا تُحذف أي مهارة بسبب تراجع ترتيبها')
    w('4. **كشف التكرار** — دمج المهارات ذات العمل نفسه وإبقاء الأقوى')
    w('5. إعادة بناء الملفات ورفع commit عند وجود تغيير فقط')
    w('')
    w('للتشغيل اليدوي: تبويب **Actions** ← **Daily skills archive update** ← **Run workflow**.')
    w('')
    w('---')
    w('')
    w('**المصدر:** https://www.skills.sh/')
    return '\n'.join(L) + '\n'


def build_changelog(date, new_rows, removed_today, first_run, total, old_path, top_n):
    e = ['## %s' % date, '']
    if first_run:
        e += ['- 📦 أول أرشفة: %s مهارة.' % num(total), '']
    else:
        if new_rows:
            e += ['### 🆕 مهارات جديدة في الأرشيف (%d)' % len(new_rows), '',
                  '| المهارة | المصدر | التثبيتات | الوصف |', '|---|---|---:|---|']
            for r in new_rows:
                e.append('| **%s** | `%s` | %s | %s |' %
                         (esc(r['name']), r['source'], num(r['installs']),
                          esc(r.get('headline') or r.get('meta') or '')[:140]))
            e.append('')
        if removed_today:
            e += ['### 🧹 مكرّرات حُذفت (%d)' % len(removed_today), '']
            for r in removed_today:
                e.append('- `%s` ← أُبقيت `%s` (%s)' % (r['id'], r['kept'], r['reason']))
            e.append('')
        if not new_rows and not removed_today:
            e += ['- ➖ لا مهارات جديدة ضمن أعلى %s؛ حُدِّثت الأرقام فقط.' % num(top_n), '']

    old = ''
    if os.path.exists(old_path):
        old = open(old_path, encoding='utf-8').read()
        old = re.sub(r'^# سجل التغييرات\n+', '', old)
        old = re.sub(r'^سجل .*?\n+', '', old, flags=re.M)
        old = re.sub(r'^الأرشيف تراكمي.*?\n+', '', old, flags=re.M)

    # إعادة التشغيل في اليوم نفسه يجب ألّا تمحو سجل اليوم ولا تستبدله:
    #   • بلا محتوى جديد  → يبقى سجل اليوم كما هو (لا نستبدله بسطر "لا جديد").
    #   • بمحتوى جديد     → يُضاف كقسم إضافي تحت نفس اليوم، لا يُستبدَل به سجل التشغيل الأول.
    same_day = re.search(r'^## %s\n(.*?)(?=^## |\Z)' % re.escape(date), old, flags=re.S | re.M)
    new_content = '\n'.join(e[2:]).rstrip()  # بدون سطر العنوان '## date' المكرّر
    if same_day:
        prev_body = same_day.group(1).rstrip()
        if not (new_rows or removed_today or first_run):
            entry = '## %s\n%s' % (date, prev_body)
        else:
            now = datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M UTC')
            entry = '## %s\n%s\n\n#### 🔁 تحديث إضافي (%s)\n\n%s' % (date, prev_body, now, new_content)
    else:
        entry = '## %s\n%s' % (date, new_content)
    old = re.sub(r'^## %s\n.*?(?=^## |\Z)' % re.escape(date), '', old, flags=re.S | re.M)

    head = ('# سجل التغييرات\n\n'
            'سجل يومي بالمهارات الجديدة الداخلة إلى الأرشيف وبالمكرّرات المحذوفة.\n'
            'الأرشيف تراكمي: لا تخرج مهارة بسبب تراجع ترتيبها.\n\n')
    return head + entry + '\n\n' + old.strip() + ('\n' if old.strip() else '')


# ------------------------------------------------------------------ main

def main():
    date = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    print('building archive for %s (top %d)' % (date, TOP_N), flush=True)

    board, total_site = leaderboard(TOP_N)
    print('leaderboard: %d entries | site total: %d' % (len(board), total_site), flush=True)
    if len(board) < TOP_N * 0.9:
        sys.exit('fatal: leaderboard returned only %d of %d expected entries' % (len(board), TOP_N))

    fresh = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for n, (sk, body, url) in enumerate(ex.map(fetch_page, board), 1):
            fresh.append(parse(sk, body, url))
            if n % 200 == 0:
                print('  parsed %d' % n, flush=True)

    snap_path = os.path.join(ROOT, 'data', 'skills.json')
    prev, prev_removed = {}, {}
    first_run = True
    if os.path.exists(snap_path):
        try:
            old = json.load(open(snap_path, encoding='utf-8'))
            prev = {r['id']: r for r in old.get('skills', [])}
            prev_removed = {k: v for k, v in (old.get('removed') or {}).items()}
            first_run = not prev
        except (ValueError, KeyError):
            pass

    # استرجاع ما فشل جلبه اليوم من لقطة الأمس
    recovered = 0
    for r in fresh:
        if not r['headline'] and r['id'] in prev:
            p = prev[r['id']]
            for k in ('headline', 'bullets', 'meta', 'stars', 'first_seen', 'audits', 'install'):
                if p.get(k):
                    r[k] = p[k]
            recovered += 1
    if recovered:
        print('recovered %d skill(s) from the previous snapshot' % recovered, flush=True)

    # ---- الدمج التراكمي: كل ما دخل الأرشيف يبقى فيه ----
    merged = {}
    for r in fresh:
        r['in_top'] = True
        r['last_updated'] = date
        r['first_archived'] = prev.get(r['id'], {}).get('first_archived', date)
        r['is_new'] = (not first_run) and r['id'] not in prev
        merged[r['id']] = r
    carried = 0
    for pid, p in prev.items():
        if pid in merged:
            continue
        p = dict(p)
        p['in_top'] = False
        p['is_new'] = False
        p.setdefault('last_updated', p.get('first_archived', date))
        merged[pid] = p
        carried += 1
    print('merged: %d fresh + %d carried over = %d' % (len(fresh), carried, len(merged)), flush=True)

    rows = sorted(merged.values(), key=lambda r: -r.get('installs', 0))

    # ---- كشف التكرار ----
    removed, flagged = find_duplicates(rows)
    rows = [r for r in rows if r['id'] not in removed]
    removed_today = [v for k, v in removed.items() if k not in prev_removed]
    print('duplicates: %d removed (%d new today) | %d flagged for review'
          % (len(removed), len(removed_today), len(flagged)), flush=True)

    new_rows = [r for r in rows if r.get('is_new')]
    print('new skills: %d | archive size: %d' % (len(new_rows), len(rows)), flush=True)

    def write(name, text):
        open(os.path.join(ROOT, name), 'w', encoding='utf-8').write(text)

    write('abbas-skills.md', build_archive_md(rows, total_site, date, removed, flagged, TOP_N))
    write('INDEX.md', build_index_md(rows, date))
    write('DUPLICATES.md', build_duplicates_md(removed, flagged, date))
    write('README.md', build_readme(rows, total_site, date, new_rows, removed, TOP_N))
    write('CHANGELOG.md', build_changelog(date, new_rows, removed_today, first_run, len(rows),
                                          os.path.join(ROOT, 'CHANGELOG.md'), TOP_N))
    json.dump({'generated_at': date, 'total_site_skills': total_site, 'top_n': TOP_N,
               'skills': rows, 'removed': removed},
              open(snap_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    missing = sum(1 for r in rows if not r.get('headline'))
    print('done — %d skills archived, %d without a description' % (len(rows), missing), flush=True)

    out = os.environ.get('GITHUB_OUTPUT')
    if out:
        with open(out, 'a', encoding='utf-8') as fh:
            fh.write('new_count=%d\n' % len(new_rows))
            fh.write('dup_count=%d\n' % len(removed_today))
            fh.write('archive_size=%d\n' % len(rows))


if __name__ == '__main__':
    main()
