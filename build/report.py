"""Generate SC100_REVIEW_REPORT.md from the review record and the bank."""
import json, os
from collections import Counter

import paths
import review as review_mod

bank = json.load(open(paths.BANK, encoding='utf-8'))
items = bank['items']
index = {'%s/%d' % (i['sec'], i['num']): i for i in items}
entries = review_mod.load()

SECTION_NAME = {'cs1': 'Fabrikam case study', 'cs2': 'Litware case study',
                'std': 'Standalone'}


def label(key):
    i = index[key]
    return '%s %d' % (SECTION_NAME[i['sec']], i['num'])


def answer_of(item, letters):
    letters = [l for l in (letters or '').split() if l]
    if not letters:
        return '—'
    out = []
    for l in letters:
        opt = (item.get('o') or [])[ord(l) - 65] if item.get('o') else None
        out.append('%s. %s' % (l, opt[:60]) if opt else l)
    return '<br>'.join(out)


status_count = Counter(e['status'] for e in entries.values())
scorable = [i for i in items if i.get('o') or i.get('boxes')]
unreviewed = len(items) - len(entries)

rows = []
for key in sorted(entries, key=lambda k: (index[k]['sec'], index[k]['num'])):
    e, item = entries[key], index[key]
    if e['status'] == 'CORRECTED':
        original = answer_of(item, e['originalAnswer'])
        final = answer_of(item, e['answer'])
    else:
        original = final = answer_of(item, item.get('a'))
    reason = e['explanation'].replace(review_mod.CORRECTION_BANNER, '').strip()
    reason = ' '.join(reason.split())
    if len(reason) > 260:
        reason = reason[:257].rsplit(' ', 1)[0] + '…'
    src = e.get('source') or {}
    link = '[%s](%s)' % (src.get('title', 'Microsoft Learn'), src['url']) if src.get('url') else '—'
    rows.append('| %s | %s | %s | %s | %s | %s | %s |'
                % (label(key), original, final, e['status'], e['confidence'], reason, link))

md = """# SC-100 answer-key review

An independent review of this bank's answer keys against current Microsoft
documentation. The bank is a third-party exam dump: its keys are not
authoritative, and this file records which of them have actually been checked.

**Reviewed on:** 2026-09-07
**Objectives used:** [SC-100 study guide, skills measured as of July 28, 2026](https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/sc-100)

## Coverage

| | Count |
| --- | --- |
| Questions in the bank | %d |
| Of those, scorable (have a gradeable key) | %d |
| **Answer keys examined against Microsoft Learn** | **%d** |
| — verified correct | %d |
| — corrected | %d |
| — flagged for manual review | %d |
| **Not yet reviewed** | **%d** |

> **Read this before trusting a key.** %d of %d keys have been checked. The
> remaining %d are reproduced from the dump exactly as it had them and have
> **not** been independently verified. The simulator says so on every question:
> a reviewed item shows its verdict and a Microsoft Learn link with the answer,
> and an unreviewed item shows only what the source recorded.

## Also corrected

**Domain weightings.** The weighted practice exam drew questions on the wrong
proportions — 30–35%% for security operations and 20–25%% for infrastructure.
The current study guide gives 20–25 / 25–30 / 25–30 / 20–25, so the 50-question
draw changed from 11/17/11/11 to 11/14/14/11.

## Findings

| Question | Original answer | Final answer | Status | Confidence | Reason | Official source |
| --- | --- | --- | --- | --- | --- | --- |
%s

## Status vocabulary

| Status | Meaning |
| --- | --- |
| `VERIFIED` | The dump's key was checked against Microsoft documentation and is right. |
| `CORRECTED` | The dump's key was wrong. The bank grades the corrected answer, and the explanation opens with `THIS ANSWER WAS CORRECTED BY AI`. |
| `MANUAL_REVIEW` | Microsoft's documentation does not settle it. The key is left exactly as the dump had it, and the question is flagged in the simulator. |
| `AMBIGUOUS` | More than one answer is defensible as the question is worded. |
| `OUTDATED` | The item tests something that has since changed. |
| `NOT_REVIEWED` | Not yet examined. The default for every question absent from `build/review.json`. |

Confidence is `HIGH` when Microsoft documentation states the point explicitly,
`MEDIUM` when it is strongly supported but needs interpretation, and `LOW` when
the documentation is ambiguous or silent. A `LOW` finding is never allowed to
stand as `VERIFIED` or `CORRECTED` — the build refuses it.

## How to continue the review

Add an entry to `build/review.json` keyed `"<section>/<number>"`, then:

```bash
python build/bank.py && python build/assemble.py && python build/test_bank.py
```

`bank.py` refuses to build if an entry contradicts the question it names — a
wrong `originalAnswer`, a letter the question does not offer, a `LOW`-confidence
verdict presented as settled, or a `VERIFIED`/`CORRECTED` entry without a
`learn.microsoft.com` source. `test_bank.py` then checks that corrections
reached the published page and that the correction banner appears on corrected
questions and nowhere else.
""" % (len(items), len(scorable), len(entries),
       status_count.get('VERIFIED', 0), status_count.get('CORRECTED', 0),
       status_count.get('MANUAL_REVIEW', 0) + status_count.get('AMBIGUOUS', 0),
       unreviewed,
       len(entries), len(items), unreviewed,
       '\n'.join(rows))

out = os.path.join(paths.ROOT, 'SC100_REVIEW_REPORT.md')
open(out, 'w', encoding='utf-8', newline='\n').write(md)

json_out = os.path.join(paths.ROOT, 'SC100_REVIEW_REPORT.json')
json.dump({
    'reviewedOn': '2026-09-07',
    'objectives': 'SC-100 skills measured as of July 28, 2026',
    'totals': {
        'questions': len(items), 'scorable': len(scorable),
        'examined': len(entries), 'notReviewed': unreviewed,
        **{s.lower(): status_count.get(s, 0) for s in review_mod.STATUSES}
    },
    'findings': {k: {'question': label(k), **v} for k, v in entries.items()}
}, open(json_out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

print('wrote %s and %s' % (os.path.basename(out), os.path.basename(json_out)))
print('%d examined of %d (%d verified, %d corrected, %d flagged), %d not reviewed'
      % (len(entries), len(items), status_count.get('VERIFIED', 0),
         status_count.get('CORRECTED', 0),
         status_count.get('MANUAL_REVIEW', 0) + status_count.get('AMBIGUOUS', 0),
         unreviewed))
