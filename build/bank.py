"""Turn the parsed dump into the bank the simulator ships.

Numbering follows the source: each section counts from 1, so an item is
identified by its section and its number there, and `n` is an internal id used
only for ordering and saved state.

Three shapes come out:
  choice - stem, lettered options, answer key. Graded.
  match  - drop-downs with a correct value per box. Graded all-or-nothing.
           Only where the real choice lists are known; the dump records these
           as pictures, so most answer areas cannot become one.
  info   - no gradeable question. The dump's answer for these is a graphic, so
           the graphic is shown on reveal rather than an invented key.
"""
import json, os, re
from collections import Counter

import paths

parsed = json.load(open(paths.PARSED, encoding='utf-8'))
imgmap = json.load(open(paths.IMGMAP, encoding='utf-8'))

CASE_META = {'cs1': {'n': 1, 'name': 'Fabrikam, Inc.'},
             'cs2': {'n': 2, 'name': 'Litware, Inc.'}}

# Answer areas whose real choice lists are known from outside the dump, which
# is the only way one can be graded — the dump itself draws them as pictures.
ANSWER_AREAS = {
    ('std', 2): [
        {'label': 'To automate vulnerability code scanning',
         'value': 'GitHub Enterprise Cloud',
         'options': ['GitHub Enterprise Cloud', 'GitHub Enterprise Server', 'GitHub Team']},
        {'label': 'To automatically generate pull requests',
         'value': 'Dependabot',
         'options': ['Dependabot', 'Codespaces', 'Dependency Tracker']}
    ],
    ('std', 3): [
        {'label': 'For NIST',
         'value': 'Microsoft Defender for Cloud',
         'options': ['Microsoft Defender for Cloud',
                     'Microsoft Defender Vulnerability Management',
                     'Microsoft Sentinel']},
        {'label': 'For GDPR',
         'value': 'Microsoft Purview Compliance Manager',
         'options': ['Microsoft Priva',
                     'Microsoft Purview Communication Compliance',
                     'Microsoft Purview Compliance Manager']}
    ]
}
AREA_NOTE = ('The choices for this item were supplied from outside the dump; the dump itself '
             'records the answer only as the picture shown above. Grading uses those choices.')

PRIOR_NOTE = ('The dump records this answer as a picture, shown above. The values below come '
              'from a text export of the same dump, which spelled them out. No list of '
              'alternatives survives anywhere, so each drop-down offers this item’s own '
              'values — match each one to its box.')

# Answer-area values recovered from the earlier text-only export of this dump,
# keyed "<section>/<number>".
_prior = json.load(open(paths.PRIOR_AREAS, encoding='utf-8'))
PRIOR_BOXES = {(k.split('/')[0], int(k.split('/')[1])): v for k, v in _prior.items()}


def conv(nodes):
    """Map extracted nodes onto what the page renders, dropping images that
    were filtered out of the re-encoded set."""
    out = []
    for n in nodes:
        if 'img' in n:
            e = imgmap.get(n['img'])
            if not e:
                continue
            out.append({'img': 'img/' + e[0], 'w': e[2], 'h': e[3]})
        else:
            t = n['p'].strip()
            if t:
                out.append({'p': t})
    return out


items = []
for q in parsed['questions']:
    sec, num = q['sec'], q['num']
    item = {'n': len(items) + 1, 'sec': sec, 'num': num, 'c': q['c']}
    if sec in CASE_META:
        item['cs'] = CASE_META[sec]

    body = conv(q['body'])
    item['body'] = body
    # A one-line summary for the review screen and the resume banner.
    first = next((n['p'] for n in reversed(body) if 'p' in n and n['p'].endswith('?')), None)
    item['q'] = first or next((n['p'] for n in body if 'p' in n), '(see question)')

    letters = [x for x in re.split(r'[,\s]+', q['a'] or '') if x]
    valid = [l for l, _ in q['o']]
    if q['o'] and letters and all(x in valid for x in letters):
        item['o'] = [t for _, t in q['o']]
        item['a'] = ' '.join(letters)
    elif (sec, num) in ANSWER_AREAS:
        boxes = ANSWER_AREAS[(sec, num)]
        for b in boxes:
            assert b['value'] in b['options'], 'answer area %s %d is inconsistent' % (sec, num)
        item['boxes'] = boxes
        item['keynote'] = AREA_NOTE
    elif (sec, num) in PRIOR_BOXES:
        # An earlier, text-only export of the same dump spelled these answer
        # areas out as "<label>: <value>" lines. The dump proper draws them, so
        # the values survive only here — keeping them means the item stays
        # gradeable, and the recorded graphic is shown alongside on reveal.
        item['boxes'] = PRIOR_BOXES[(sec, num)]
        item['keynote'] = PRIOR_NOTE

    ans = conv(q['ansimg'])
    if ans:
        item['ansimg'] = ans
    expl = conv(q['e'])
    if expl:
        item['e'] = expl
    items.append(item)

cases = {k: conv(v) for k, v in parsed['cases'].items()}
for k, v in cases.items():
    CASE_META[k]['nodes'] = v

choice = sum(1 for i in items if 'o' in i)
match = sum(1 for i in items if 'boxes' in i)
info = len(items) - choice - match
print('total %d | choice %d | match %d | info %d' % (len(items), choice, match, info))
print('scored: %d' % (choice + match))
print('info items that now show a recorded answer: %d'
      % sum(1 for i in items if 'o' not in i and 'boxes' not in i and i.get('ansimg')))
print('items carrying an exhibit: %d' % sum(1 for i in items if any('img' in n for n in i['body'])))
print('items carrying an explanation: %d' % sum(1 for i in items if i.get('e')))
print('per section:', Counter(i['sec'] for i in items))
print('per domain:', Counter(i['c'] for i in items))
print('case narrative nodes:', {k: len(v) for k, v in cases.items()})

json.dump({'items': items, 'cases': CASE_META},
          open(paths.BANK, 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
