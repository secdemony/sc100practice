# Building the simulator

`index.html` is generated, not hand-written. It is ~500 KB with the whole
question bank embedded in it, so editing it directly is a bad idea: the next
rebuild silently overwrites the change. Edit the sources here and rebuild.

## Rebuilding the page only

This is what you want for a wording, styling or behaviour change. It needs
nothing but this directory — no PDF, no image processing.

```bash
python build/assemble.py
```

It reads `build/bank.json` (the parsed questions, committed) plus `app.js`,
`extra.css` and `base.css.html`, and writes `index.html`. `img/` is left alone,
and it warns if the bank references an image that isn't there.

Set `SC100_COPY_TO` to also drop a copy somewhere convenient:

```bash
SC100_COPY_TO=~/Downloads/simulator.html python build/assemble.py
```

## Rebuilding everything from the source PDF

Needed only when the questions themselves change. Expects the dump at
`../Microsoft-SC-100_unlocked.pdf` (a sibling of the repo directory); override
with `SC100_PDF`. Requires `pymupdf` and `Pillow`.

```bash
python build/extract.py    # PDF  -> text blocks + exhibit images, with positions
python build/build4.py     #      -> 310 parsed questions
python build/shrink.py     #      -> exhibits re-encoded to WebP
python build/bank.py       #      -> build/bank.json
python build/assemble.py   #      -> index.html + img/
```

Run in that order; each step reads the previous one's output from
`build/_work/` (gitignored). The whole chain takes a few minutes, most of it in
`extract.py`.

## What each piece is

| File | Role |
| --- | --- |
| `paths.py` | Every path in one place, so no script carries an absolute one |
| `extract.py` | Walks the PDF in reading order, emitting text and images interleaved — that ordering is the only thing tying an exhibit to its question |
| `build4.py` | Splits that stream into questions: body, options, answer, explanation, plus the two case-study narratives |
| `shrink.py` | Re-encodes referenced images to WebP at 1000px wide, and applies `clean/overrides.json` |
| `bank.py` | Assembles the final bank: question shapes, answer areas, per-section numbering |
| `assemble.py` | Stitches the bank, `app.js` and the CSS into `index.html`, and syncs `img/` |
| `app.js` | The simulator itself |
| `extra.css` | Styles added on top of `base.css.html` |
| `base.css.html` | Base stylesheet, inherited from the Security+ simulator this was built from |
| `bank.json` | The parsed bank. Committed so the page can be rebuilt without the PDF |
| `prior-answer-areas.json` | 23 answer-area items whose values survive only in an earlier text export of the dump. Without this they would stop being gradeable |
| `clean/` | Unwatermarked replacements for exhibits, mapped to the extracted filename each stands in for |

## Things worth knowing before changing anything

- **Numbering follows the source.** The dump numbers each of its three sections
  from 1, so a question is identified by section + number, never by number
  alone. `n` is an internal id used for ordering and saved state.
- **Exhibits are files, not data URIs.** 345 images come to 8 MB; inlined that
  is an 11 MB page that must download in full before the first question
  appears. `index.html` therefore needs `img/` beside it.
- **88 items are deliberately not scored.** The dump draws their answers rather
  than writing them, so there is nothing to grade. They show the recorded
  graphic on reveal. Do not invent keys for them.
- **Storage keys are versioned** (`sc100-*-v2`). If question numbering ever
  changes again, bump them, or saved progress will point at the wrong items.
- **Answers are reproduced as-is.** Where the dump contradicts itself, it is
  left alone rather than second-guessed.
