"""Build the SC-100 bank from the complete dump.

The earlier bank came from a text-only export that had dropped the scenario
paragraphs, every diagram, and most explanations, leaving stems that read as
fragments. This reads the full PDF instead, so a question arrives with the text
the exam actually shows, the exhibit it refers to, the answer the dump records —
including the answer-area graphics that no amount of text extraction could
recover — and the explanation.

A question body is an ordered list of nodes ({"p": text} or {"img": file}) so
prose and diagrams stay in the order the page presents them.
"""
import json, os, re
from collections import Counter

import paths

blocks = json.load(open(paths.BLOCKS, encoding='utf-8'))

FURNITURE = {'Microsoft - SC-100', 'Braindumps Questions',
             '100% Success with DumpsPedia.com'}
PAGENO = re.compile(r'^\d+ of \d+$')
HEAD = re.compile(r'^Question #:(\d+)\s*-?\s*$')
CAT = re.compile(r'^\s*-\s*\[(.+)\]\s*$')
TOPIC = re.compile(r'^\(Exam Topic (\d)\)\s*$')
OPTLETTER = re.compile(r'^([A-J])\.$')
ANSWER = re.compile(r'^Answer:\s*(.*)$')
SECTION = re.compile(r'^Topic (\d), (.+)$')


def clean(s):
    s = s.replace('\xa0', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    # The layout pass sprays stray spaces through URLs ("ht tps://", "az ure").
    # A URL never contains a space, so a line that is one gets them removed.
    if re.match(r'^h\s*t\s*t\s*p', s, re.I) and ' ' in s:
        s = re.sub(r'\s+', '', s)
    return s


def is_noise(s):
    t = s.strip()
    return (not t) or t in FURNITURE or bool(PAGENO.match(t)) or t.startswith('100% Success with')


def is_marker(s):
    return bool(HEAD.match(s) or CAT.match(s) or TOPIC.match(s) or ANSWER.match(s)
                or OPTLETTER.match(s) or SECTION.match(s)) or s == 'Explanation'


def paragraphs(lines):
    """Rejoin a PDF block's wrapped lines into paragraphs.

    The block is the PDF's own paragraph unit, so lines inside it belong
    together — except bullet items and structural markers, which each begin a
    paragraph of their own however the layout engine happened to wrap them.
    """
    out, buf = [], []
    for raw in lines:
        if is_noise(raw):
            continue
        s = clean(raw)
        if not s:
            continue
        if s.startswith('•') or is_marker(s):
            if buf:
                out.append(' '.join(buf))
                buf = []
            out.append(s)
        else:
            buf.append(s)
    if buf:
        out.append(' '.join(buf))
    return out


SECTION_KEY = {1: 'cs1', 2: 'cs2', 3: 'std'}

state = {'sec': None, 'cur': None, 'mode': None}
cases = {}
questions = []


def flush():
    if state['cur']:
        questions.append(state['cur'])
        state['cur'] = None


def handle_text(s):
    sec, cur, mode = state['sec'], state['cur'], state['mode']

    m = SECTION.match(s)
    if m and ('Case Study' in s or 'Standalone' in s):
        flush()
        state['sec'] = SECTION_KEY[int(m.group(1))]
        if state['sec'] != 'std':
            cases[state['sec']] = []
        state['mode'] = None
        return

    m = HEAD.match(s)
    if m:
        flush()
        state['cur'] = {'sec': sec, 'num': int(m.group(1)), 'c': '',
                        'body': [], 'o': [], 'a': '', 'ansimg': [], 'e': []}
        state['mode'] = 'body'
        return

    if cur is None:
        if sec in cases:
            cases[sec].append({'p': s})
        return

    m = CAT.match(s)
    if m and not cur['c']:
        cur['c'] = m.group(1).strip()
        return
    if TOPIC.match(s):
        return

    m = ANSWER.match(s)
    if m:
        cur['a'] = m.group(1).strip()
        state['mode'] = 'answer'
        return

    if s == 'Explanation':
        state['mode'] = 'expl'
        return

    # Prose sitting between a lettered answer and the "Explanation" heading is
    # explanation text the dump forgot to label, so it is kept as such.
    if mode in ('expl', 'answer'):
        cur['e'].append({'p': s})
        return

    m = OPTLETTER.match(s)
    if m:
        cur['o'].append([m.group(1), ''])
        state['mode'] = 'opts'
        return

    if mode == 'opts' and cur['o']:
        last = cur['o'][-1]
        last[1] = (last[1] + ' ' + s).strip() if last[1] else s
        return

    cur['body'].append({'p': s})


for b in blocks:
    if b['t'] == 'img':
        node = {'img': b['file'], 'w': b['w'], 'h': b['h']}
        cur, mode = state['cur'], state['mode']
        if cur is None:
            if state['sec'] in cases:
                cases[state['sec']].append(node)
        elif mode == 'expl':
            cur['e'].append(node)
        elif mode == 'answer':
            cur['ansimg'].append(node)
        else:
            cur['body'].append(node)
        continue
    for s in paragraphs(b['lines']):
        handle_text(s)

flush()

LETTERS = re.compile(r'^[A-J](\s*,?\s*[A-J])*$')
print('questions parsed:', len(questions))
print('per section:', Counter(q['sec'] for q in questions))
print('with options:', sum(1 for q in questions if q['o']))
print('with lettered answer:', sum(1 for q in questions if LETTERS.match(q['a'] or '')))
print('with answer image:', sum(1 for q in questions if q['ansimg']))
print('with explanation:', sum(1 for q in questions if q['e']))
print('body images:', sum(1 for q in questions for n in q['body'] if 'img' in n))
print('case narrative nodes:', {k: len(v) for k, v in cases.items()})
print('missing category:', sum(1 for q in questions if not q['c']))
print('empty body:', sum(1 for q in questions if not q['body']))
print('odd answers:', [(q['sec'], q['num'], q['a']) for q in questions
                       if q['a'] and not LETTERS.match(q['a'])][:10])

json.dump({'questions': questions, 'cases': cases},
          open(paths.PARSED, 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
