"""Invariants the bank and the answer-key review must hold.

Run with `python build/test_bank.py`. Exits non-zero on the first failing
invariant, so it works as a build gate.

The point of most of these is that a correction has to land in one place and
show up everywhere: if the graded key and the displayed explanation could ever
disagree, the simulator would teach the wrong answer while marking it wrong.
"""
import json, re, sys

import paths
import review as review_mod

FAILURES = []


def check(name, ok, detail=''):
    if ok:
        print('  ok   %s' % name)
    else:
        print('  FAIL %s%s' % (name, (': ' + detail) if detail else ''))
        FAILURES.append(name)


bank = json.load(open(paths.BANK, encoding='utf-8'))
items = bank['items']
index = {'%s/%d' % (i['sec'], i['num']): i for i in items}
entries = review_mod.load()
html = open(paths.OUT_HTML, encoding='utf-8').read()
BANNER = review_mod.CORRECTION_BANNER

print('bank integrity')

check('every item has a section, number and domain',
      all(i.get('sec') and i.get('num') and i.get('c') for i in items))

check('question numbering is contiguous within each section',
      all(sorted(i['num'] for i in items if i['sec'] == s)
          == list(range(1, 1 + max(i['num'] for i in items if i['sec'] == s)))
          for s in ('cs1', 'cs2', 'std')))

check('no two items share a section and number',
      len(index) == len(items),
      '%d items, %d distinct keys' % (len(items), len(index)))

DOMAINS = {'Design solutions that align with security best practices and priorities',
           'Design security operations, identity, and compliance capabilities',
           'Design security solutions for infrastructure',
           'Design security solutions for applications and data'}
bad_domain = [k for k, i in index.items() if i['c'] not in DOMAINS]
check('every item is in one of the four current SC-100 domains', not bad_domain, str(bad_domain[:5]))

print('answer keys')

scorable = [i for i in items if i.get('o') or i.get('boxes')]
check('every scorable item has a key',
      all((i.get('a') or '').strip() or i.get('boxes') for i in scorable))

out_of_range = []
for k, i in index.items():
    if not i.get('o'):
        continue
    n = len(i['o'])
    for letter in (i.get('a') or '').split():
        if len(letter) != 1 or not ('A' <= letter < chr(ord('A') + n)):
            out_of_range.append('%s -> %s of %d options' % (k, letter, n))
check('no key names an option the question does not have', not out_of_range, str(out_of_range[:5]))

dupes = []
for k, i in index.items():
    letters = (i.get('a') or '').split()
    if len(letters) != len(set(letters)):
        dupes.append(k)
check('no key repeats the same letter', not dupes, str(dupes[:5]))

box_bad = [k for k, i in index.items() if i.get('boxes')
           for b in i['boxes'] if b.get('options') and b['value'] not in b['options']]
check('every answer-area value is among its own options', not box_bad, str(box_bad[:5]))

print('the review record')

problems = review_mod.validate(entries, index)
check('review.json is internally consistent', not problems, '; '.join(problems[:3]))

corrected = {k for k, e in entries.items() if e['status'] == 'CORRECTED'}
check('every correction changed the graded key',
      all(index[k]['a'] == entries[k]['answer'] != entries[k]['originalAnswer']
          for k in corrected))

check('every corrected item is marked corrected in the bank',
      all((index[k].get('review') or {}).get('corrected') for k in corrected))

not_corrected = {k for k, e in entries.items() if e['status'] != 'CORRECTED'}
check('no non-corrected item is marked corrected',
      not any((index[k].get('review') or {}).get('corrected') for k in not_corrected))

check('a flagged item keeps the source key untouched',
      all(not entries[k].get('answer') for k, e in entries.items()
          if e['status'] in ('MANUAL_REVIEW', 'AMBIGUOUS')))

check('every reviewed item carries an explanation into the bank',
      all(((index[k].get('review') or {}).get('explanation') or '').strip() for k in entries))

check('every VERIFIED or CORRECTED entry cites a Microsoft Learn URL',
      all((e.get('source') or {}).get('url', '').startswith('https://learn.microsoft.com/')
          for e in entries.values() if e['status'] in ('VERIFIED', 'CORRECTED')))

print('the correction banner')

# The banner must be a claim the page can back up: present for exactly the
# items whose key actually changed, and nowhere else.
banner_in_bank = {k for k, i in index.items()
                  if BANNER in json.dumps(i.get('review') or {}, ensure_ascii=False)}
check('the banner appears only on corrected items',
      banner_in_bank <= corrected,
      'unexpected on %s' % sorted(banner_in_bank - corrected))
check('the banner appears on every corrected item',
      corrected <= banner_in_bank,
      'missing from %s' % sorted(corrected - banner_in_bank))
check('the published page contains the banner exactly once per corrected item',
      html.count(BANNER) == len(corrected) + 1,
      'found %d occurrences for %d corrections (plus one in the renderer)'
      % (html.count(BANNER), len(corrected)))

print('the published page')

check('the page embeds every item', html.count('"sec":"') >= len(items))
check('the page carries the review payload for each reviewed item',
      html.count('"review":{') == len(entries),
      'found %d, expected %d' % (html.count('"review":{'), len(entries)))

for key in sorted(corrected):
    e = entries[key]
    pattern = '"num":%d,' % index[key]['num']
    check('%s is published with the corrected key %s' % (key, e['answer']),
          ('"a":"%s"' % e['answer']) in html)

weights = re.search(r'const DOMAIN_WEIGHTS = \[(.*?)\];', html, re.S)
check('the weighted exam draws 50 questions',
      weights is not None
      and sum(int(m) for m in re.findall(r'target:(\d+)', weights.group(1))) == 50)
check('the published domain weightings match the current study guide',
      weights is not None
      and re.findall(r"pct:'([^']+)'", weights.group(1))
          == ['20–25%', '25–30%', '25–30%', '20–25%'],
      re.findall(r"pct:'([^']+)'", weights.group(1)) if weights else 'not found')

print()
if FAILURES:
    print('%d check(s) failed' % len(FAILURES))
    sys.exit(1)
print('all checks passed')
