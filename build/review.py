"""The answer-key review: what has been checked against Microsoft Learn.

`review.json` is the record. Each entry is keyed "<section>/<number>" and says
what the review concluded, how confident it is, and which Microsoft Learn page
establishes it. `bank.py` merges this into the bank, which is what makes a
correction take effect everywhere at once — the graded key, the explanation the
candidate reads, and the audit report all come from this one place, so the page
can never show one answer while the scoring engine believes another.

Status values
-------------
VERIFIED      The dump's key was checked and is right.
CORRECTED     The dump's key was wrong. `answer` replaces it.
MANUAL_REVIEW Microsoft's documentation does not settle it. The key is left
              exactly as the dump had it and the item is flagged in the UI.
AMBIGUOUS     More than one answer is defensible as written.
OUTDATED      The item tests something that has since changed.
NOT_REVIEWED  Not yet examined. The default for everything absent from the file.

Confidence
----------
HIGH    Microsoft documentation states it explicitly.
MEDIUM  Strongly supported, but needs interpretation.
LOW     Documentation is ambiguous, silent, or out of date. LOW must be paired
        with MANUAL_REVIEW: a low-confidence conclusion is not a conclusion.
"""
import json, os

import paths

STATUSES = {'VERIFIED', 'CORRECTED', 'MANUAL_REVIEW', 'AMBIGUOUS', 'OUTDATED', 'NOT_REVIEWED'}
CONFIDENCE = {'HIGH', 'MEDIUM', 'LOW'}
CORRECTION_BANNER = 'THIS ANSWER WAS CORRECTED BY AI'

REVIEW_FILE = os.path.join(paths.HERE, 'review.json')


def load():
    if not os.path.exists(REVIEW_FILE):
        return {}
    data = json.load(open(REVIEW_FILE, encoding='utf-8'))
    return {k: v for k, v in data.items() if not k.startswith('_')}


def validate(entries, bank_index):
    """Fail the build rather than ship a review record that contradicts itself.

    bank_index maps "<sec>/<num>" -> the parsed item, so a review entry can be
    checked against the question it claims to be about.
    """
    problems = []
    for key, e in sorted(entries.items()):
        item = bank_index.get(key)
        if item is None:
            problems.append('%s: no such question' % key)
            continue

        status = e.get('status')
        if status not in STATUSES:
            problems.append('%s: bad status %r' % (key, status))
        conf = e.get('confidence')
        if conf not in CONFIDENCE:
            problems.append('%s: bad confidence %r' % (key, conf))
        if conf == 'LOW' and status not in ('MANUAL_REVIEW', 'AMBIGUOUS'):
            problems.append('%s: LOW confidence must be MANUAL_REVIEW or AMBIGUOUS, not %s'
                            % (key, status))
        if not e.get('explanation'):
            problems.append('%s: no explanation' % key)

        # A cited source must be a real Microsoft Learn URL, not a plausible one.
        src = e.get('source') or {}
        url = src.get('url', '')
        if status in ('VERIFIED', 'CORRECTED'):
            if not url.startswith('https://learn.microsoft.com/'):
                problems.append('%s: %s needs a learn.microsoft.com source, got %r'
                                % (key, status, url))

        letters = [l for l in (item.get('a') or '').split() if l]
        n_opts = len(item.get('o') or [])
        if status == 'CORRECTED':
            new = [l for l in (e.get('answer') or '').split() if l]
            if not new:
                problems.append('%s: CORRECTED with no answer' % key)
            if 'originalAnswer' not in e:
                problems.append('%s: CORRECTED without recording originalAnswer' % key)
            else:
                # Before the merge the item still holds the source key; after
                # it, the source key lives on as srcA. Either way this compares
                # the review against what the dump actually said.
                source_key = item.get('srcA', item.get('a') or '')
                if e['originalAnswer'] != source_key:
                    problems.append('%s: originalAnswer %r does not match the dump key %r'
                                    % (key, e['originalAnswer'], source_key))
            if ' '.join(new) == item.get('srcA', item.get('a') or ''):
                problems.append('%s: CORRECTED but the answer is unchanged' % key)
            for l in new:
                if n_opts and (len(l) != 1 or not ('A' <= l < chr(ord('A') + n_opts))):
                    problems.append('%s: corrected answer %r is not one of its options' % (key, l))
        else:
            if e.get('answer') and e['answer'] != (item.get('a') or ''):
                problems.append('%s: %s must not change the answer' % (key, status))
    return problems


def merge(item, entry):
    """Apply one review entry to one bank item."""
    if not entry:
        return
    status = entry['status']
    review = {'status': status, 'confidence': entry['confidence'],
              'explanation': entry['explanation']}
    if entry.get('whyWrong'):
        review['whyWrong'] = entry['whyWrong']
    if entry.get('source'):
        review['source'] = entry['source']
    if status == 'CORRECTED':
        review['corrected'] = True
        review['originalAnswer'] = entry['originalAnswer']
        text = review['explanation'].strip()
        if not text.startswith(CORRECTION_BANNER):
            review['explanation'] = CORRECTION_BANNER + '\n\n' + text
        item['srcA'] = item.get('a') or ''      # what the dump said, kept for the audit
        item['a'] = entry['answer']
    item['review'] = review
