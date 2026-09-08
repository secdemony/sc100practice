"""Assemble the SC-100 simulator and its image folder."""
import json, io, os, shutil

import paths

HERE = paths.HERE
OUT_HTML = paths.OUT_HTML
OUT_IMG = paths.OUT_IMG
# Optional convenience copy, e.g. SC100_COPY_TO=~/Downloads/simulator.html
LOCAL_COPY = os.environ.get('SC100_COPY_TO')


def rd(name):
    return open(os.path.join(HERE, name), encoding='utf-8').read()


bank = json.load(open(paths.BANK, encoding='utf-8'))
items, cases = bank['items'], bank['cases']
items.sort(key=lambda q: q['n'])

ORDER = ['n', 'sec', 'num', 'c', 'q', 'body', 'o', 'a', 'srcA', 'boxes', 'order', 'keynote',
         'review', 'ansimg', 'e', 'cs']
lines = [json.dumps({k: q[k] for k in ORDER if k in q}, ensure_ascii=False, separators=(',', ':'))
         for q in items]
bank_js = 'const QUESTIONS = [\n' + ',\n'.join(lines) + '\n];\n'
cases_js = ('\n// The two case-study scenarios, shown from a panel on their questions.\n'
            'const CASES = ' +
            json.dumps({k: v['nodes'] for k, v in cases.items()},
                       ensure_ascii=False, separators=(',', ':')) + ';\n')

choice = sum(1 for q in items if 'o' in q)
match = sum(1 for q in items if 'boxes' in q)
order_n = sum(1 for q in items if 'order' in q)
unscored = len(items) - choice - match - order_n
exhibits = sum(1 for q in items if any('img' in n for n in q['body']))
explained = sum(1 for q in items if q.get('e'))
reviewed = sum(1 for q in items if q.get('review'))
corrected_n = sum(1 for q in items if (q.get('review') or {}).get('corrected'))
flagged = sum(1 for q in items
              if (q.get('review') or {}).get('status') in ('MANUAL_REVIEW', 'AMBIGUOUS'))
consts = (
    '\n// How the bank breaks down, for the copy on the setup screen.\n'
    'const CHOICE_COUNT = %d;\n'
    'const MATCH_COUNT = %d;\n'
    'const ORDER_COUNT = %d;\n'
    'const SCORABLE_COUNT = %d;\n'
    '// Answer-area items whose answers the source draws rather than writes.\n'
    'const UNSCORED_COUNT = %d;\n'
    'const EXHIBIT_COUNT = %d;\n'
    'const EXPLAINED_COUNT = %d;\n'
    '// Answer keys checked against Microsoft Learn (build/review.json).\n'
    'const REVIEWED_COUNT = %d;\n'
    'const CORRECTED_COUNT = %d;\n'
    'const FLAGGED_COUNT = %d;\n\n'
) % (choice, match, order_n, choice + match + order_n, unscored, exhibits, explained,
     reviewed, corrected_n, flagged)

css = rd('base.css.html')
for old, new in [('--navy:#1a2942;', '--navy:#1b3a5c;'),
                 ('--navy-light:#243a5e;', '--navy-light:#26527d;'),
                 ('--accent:#2563eb;', '--accent:#0f6cbd;'),
                 ('--accent-light:#dbeafe;', '--accent-light:#deecf9;')]:
    assert old in css, 'palette swap target missing: ' + old
    css = css.replace(old, new)
css = css.replace('</style>', rd('extra.css') + '</style>')

html = (
    '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
    '<meta charset="UTF-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    '<title>Microsoft SC-100 Practice Simulator</title>\n'
    + css +
    '</head>\n<body>\n<div id="app"></div>\n\n<script>\n'
    + bank_js + cases_js + consts + rd('app.js') +
    '</script>\n</body>\n</html>\n'
)

with io.open(OUT_HTML, 'w', encoding='utf-8', newline='\n') as f:
    f.write(html)
if LOCAL_COPY:
    shutil.copyfile(OUT_HTML, LOCAL_COPY)

# Exhibits ship beside the page rather than inlined: 345 of them come to 8 MB,
# which as base64 would be an 11 MB page that has to download in full before the
# first question appears. As files they load lazily, one question at a time.
os.makedirs(OUT_IMG, exist_ok=True)
used = set()
for q in items:
    for key in ('body', 'ansimg', 'e'):
        for n in q.get(key, []):
            if 'img' in n:
                used.add(os.path.basename(n['img']))
for nodes in (v['nodes'] for v in cases.values()):
    for n in nodes:
        if 'img' in n:
            used.add(os.path.basename(n['img']))
have_webp = os.path.isdir(paths.WEBP)
if have_webp:
    for name in sorted(os.listdir(OUT_IMG)):
        if name not in used:
            os.remove(os.path.join(OUT_IMG, name))
    total = 0
    for name in sorted(used):
        shutil.copyfile(os.path.join(paths.WEBP, name), os.path.join(OUT_IMG, name))
        total += os.path.getsize(os.path.join(OUT_IMG, name))
else:
    # No re-encoded images to hand: this is a page-only rebuild from the
    # committed bank, so img/ is left exactly as it is. Missing files are worth
    # saying out loud rather than discovering as broken exhibits in the browser.
    total = sum(os.path.getsize(os.path.join(OUT_IMG, n))
                for n in os.listdir(OUT_IMG)) if os.path.isdir(OUT_IMG) else 0
    missing = [n for n in sorted(used) if not os.path.exists(os.path.join(OUT_IMG, n))]
    print('note: no %s, so img/ was left untouched (page-only rebuild)'
          % os.path.relpath(paths.WEBP, paths.ROOT))
    if missing:
        print('WARNING: %d referenced image(s) are not in img/, e.g. %s'
              % (len(missing), ', '.join(missing[:3])))

print('wrote %s (%d KB)' % (OUT_HTML, len(html.encode('utf-8')) // 1024))
print('%d questions: %d choice + %d answer-area + %d ordering = %d scored, %d unscored'
      % (len(items), choice, match, order_n, choice + match + order_n, unscored))
print('review: %d keys checked, %d corrected, %d flagged' % (reviewed, corrected_n, flagged))
print('%d exhibits, %d explanations, %d images (%.1f MB) in img/'
      % (exhibits, explained, len(used), total / 1e6))
