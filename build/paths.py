"""Where everything lives, so no script carries an absolute path.

Intermediates go under build/_work/ and are not committed: they are large and
entirely derived. The two artefacts that ARE committed — build/bank.json and the
published page — sit outside it, so a change to either shows up in a diff.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))     # build/
ROOT = os.path.dirname(HERE)                          # repo root
WORK = os.path.join(HERE, '_work')                    # derived, gitignored

# Inputs
# The source dump. Override with SC100_PDF when it lives somewhere else; the
# default assumes it sits next to the repo directory.
PDF = os.environ.get('SC100_PDF') or os.path.join(
    os.path.dirname(ROOT), 'Microsoft-SC-100_unlocked.pdf')
PRIOR_AREAS = os.path.join(HERE, 'prior-answer-areas.json')

# Intermediates
BLOCKS = os.path.join(WORK, 'blocks.json')
PARSED = os.path.join(WORK, 'parsed.json')
IMGMAP = os.path.join(WORK, 'imgmap.json')
DUMPIMG = os.path.join(WORK, 'dumpimg')               # images as extracted
WEBP = os.path.join(WORK, 'webp')                     # images re-encoded

# Committed artefacts
BANK = os.path.join(HERE, 'bank.json')
OUT_HTML = os.path.join(ROOT, 'index.html')
OUT_IMG = os.path.join(ROOT, 'img')

os.makedirs(WORK, exist_ok=True)
