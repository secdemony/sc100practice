"""Find answer keys worth suspecting, without reading a single doc.

A dump's wrong keys are not evenly spread: they cluster where the bank
contradicts itself. This finds those spots so the expensive work — checking a
key against Microsoft Learn — can be aimed rather than spread evenly over 222
questions.

None of these findings is proof of an error. They are leads, ranked.

Run: python build/triage.py
"""
import json, re
from collections import defaultdict

import paths
import review as review_mod

items = json.load(open(paths.BANK, encoding='utf-8'))['items']
choice = [i for i in items if i.get('o')]
reviewed = set(review_mod.load())


def key(i):
    return '%s/%d' % (i['sec'], i['num'])


def label(i):
    return '%s %d' % ({'cs1': 'Fabrikam', 'cs2': 'Litware', 'std': 'Standalone'}[i['sec']], i['num'])


def body(i):
    return ' '.join(n.get('p', '') for n in i['body'])


def expl(i):
    return ' '.join(n.get('p', '') for n in i.get('e', []))


findings = defaultdict(list)

# ---------------------------------------------------------------------------
# 1. The key names a different number of answers than the stem asks for.
#    This is the one check that is close to proof: "choose two" with one letter
#    means the dump lost an option or lost half the key.
# ---------------------------------------------------------------------------
WORDS = {'two': 2, 'three': 3, 'four': 4}
ASKS = re.compile(r'\b(?:which|select|choose|include|recommend|perform)\s+(?:\w+\s+){0,3}?(two|three|four)\b')
for i in choice:
    m = ASKS.search(body(i).lower())
    if not m:
        continue
    want, got = WORDS[m.group(1)], len(i['a'].split())
    if want != got:
        findings['key count disagrees with the stem'].append(
            '%s: stem asks for %s, key has %d (%s)' % (label(i), m.group(1), got, i['a']))

# ---------------------------------------------------------------------------
# 2. The same question appears twice with different keys. One of them is wrong.
# ---------------------------------------------------------------------------
by_shape = defaultdict(list)
for i in choice:
    opts = tuple(sorted(o.lower().strip() for o in i['o']))
    if opts == ('no', 'yes'):
        continue                     # handled below; every one of these matches
    stem = ' '.join(re.sub(r'[^a-z ]', '', body(i).lower()).split()[-14:])
    by_shape[(opts, stem)].append(i)
for group in by_shape.values():
    if len(group) > 1 and len({g['a'] for g in group}) > 1:
        findings['duplicate question, conflicting keys'].append(
            ', '.join('%s=%s' % (label(g), g['a']) for g in group))

# ---------------------------------------------------------------------------
# 3. The source's own explanation argues for an option other than the key.
#    Scored by how much of each option's wording turns up in the explanation.
# ---------------------------------------------------------------------------
for i in choice:
    e = expl(i).lower()
    letters = i['a'].split()
    if len(e) < 60 or len(letters) != 1:
        continue
    scores = []
    for opt in i['o']:
        words = [w for w in re.sub(r'[^a-z0-9 ]', '', opt.lower()).split() if len(w) > 4]
        scores.append(sum(w in e for w in words) / len(words) if words else 0)
    keyed = ord(letters[0]) - 65
    best = max(scores)
    if best > 0.5 and scores[keyed] < best - 0.34:
        findings['explanation points at another option'].append(
            '%s: keyed %s, explanation reads like %s'
            % (label(i), letters[0], chr(65 + scores.index(best))))

# ---------------------------------------------------------------------------
# 4. Repeated-scenario ("does this meet the goal?") families.
#    NOT an error signal on its own: Microsoft's format allows more than one
#    proposed solution to be correct. A family with no Yes at all is the odd
#    one, and usually means the family is split across the bank.
# ---------------------------------------------------------------------------
fam = defaultdict(list)
for i in choice:
    if [o.lower().strip() for o in i['o']] != ['yes', 'no']:
        continue
    head = re.split(r'Solution:', body(i))[0]
    fam[' '.join(re.sub(r'[^a-z ]', '', head.lower()).split()[:14])].append(i)
for members in fam.values():
    if len(members) < 2:
        continue
    yes = [m for m in members if m['a'] == 'A']
    if not yes:
        findings['Yes/No family with no correct solution'].append(
            ', '.join(label(m) for m in members))

# ---------------------------------------------------------------------------
# 5. Keys that are suspiciously lopsided within a question's option count —
#    a weak signal, reported last, and only for questions nobody has looked at.
# ---------------------------------------------------------------------------
unreviewed = [i for i in choice if key(i) not in reviewed]

ORDER = ['key count disagrees with the stem',
         'duplicate question, conflicting keys',
         'explanation points at another option',
         'Yes/No family with no correct solution']

print('Triage over %d lettered-choice questions (%d already reviewed).\n'
      % (len(choice), len(choice) - len(unreviewed)))
total = 0
for name in ORDER:
    hits = findings.get(name, [])
    total += len(hits)
    print('%s: %d' % (name, len(hits)))
    for h in hits:
        print('    %s' % h)
    print()
print('%d lead(s). None is proof of an error - each still needs checking against'
      % total)
print('Microsoft Learn before any key is changed.')
print('%d of %d keys remain unreviewed.' % (len(unreviewed), len(choice)))
