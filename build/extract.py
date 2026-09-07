"""Pull the SC-100 dump apart into text blocks and exhibit images.

The dump is a paginated PDF, so a question's text and the diagrams belonging to
it are only related by where they sit on the page. This walks every page in
reading order, emitting text lines and image placeholders interleaved, so the
parser downstream can tell which exhibit belongs to which question rather than
guessing from page numbers.
"""
import json, os, re
import pymupdf

import paths

SRC = paths.PDF
IMGDIR = paths.DUMPIMG
os.makedirs(IMGDIR, exist_ok=True)

# Page furniture: the vendor's header and footer banners repeat on every page at
# a fixed size, and the running head/foot lines say the same thing 246 times.
FURNITURE_SIZES = {(485, 120)}
FOOTER = re.compile(
    r'^\s*(100% Success with DumpsPedia\.com|Braindumps Questions\s+Microsoft - SC-100|\d+ of \d+)\s*$')
# Some lines carry the page number welded onto real content by the layout pass.
TRAILING_PAGENO = re.compile(r'\s{2,}\d{1,3} of \d{3}\s*$')
LEADING_FOOTER = re.compile(r'^\s*100% Success with DumpsPedia\.com\s*')

doc = pymupdf.open(SRC)
blocks = []          # ordered stream of {'t':'text','s':..} / {'t':'img','file':..}
kept_images = 0

for pno in range(doc.page_count):
    page = doc[pno]
    items = []

    # Text blocks with their vertical position.
    for b in page.get_text('blocks'):
        x0, y0, x1, y1, text, bno, btype = b
        if btype != 0:
            continue
        items.append((y0, x0, 'text', text))

    # Images, with the rectangle each one actually occupies on this page.
    for info in page.get_images(full=True):
        xref = info[0]
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []
        if not rects:
            continue
        try:
            pix = pymupdf.Pixmap(doc, xref)
        except Exception:
            continue
        if (pix.width, pix.height) in FURNITURE_SIZES:
            continue
        # Drop hairlines and bullet glyphs; a real exhibit is never this small.
        if pix.width < 200 or pix.height < 60:
            continue
        name = 'p%03d_x%d.png' % (pno + 1, xref)
        path = os.path.join(IMGDIR, name)
        if not os.path.exists(path):
            if pix.n - pix.alpha >= 4:      # CMYK needs converting before PNG
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            pix.save(path)
        kept_images += 1
        r = rects[0]
        items.append((r.y0, r.x0, 'img', {'file': name, 'w': pix.width, 'h': pix.height}))

    items.sort(key=lambda it: (round(it[0], 1), it[1]))
    for _, _, kind, payload in items:
        if kind == 'img':
            blocks.append({'t': 'img', 'page': pno + 1, **payload})
        else:
            # Keep the PDF's own block grouping: a block is a paragraph, and
            # rejoining its wrapped lines is the parser's job, not this one's.
            lines = []
            for line in payload.split('\n'):
                line = LEADING_FOOTER.sub('', line)
                line = TRAILING_PAGENO.sub('', line)
                if FOOTER.match(line):
                    continue
                if line.strip():
                    lines.append(line.rstrip())
            if lines:
                blocks.append({'t': 'text', 'page': pno + 1, 'lines': lines})

json.dump(blocks, open(paths.BLOCKS, 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
print('pages %d | text lines %d | images kept %d'
      % (doc.page_count,
         sum(1 for b in blocks if b['t'] == 'text'),
         sum(1 for b in blocks if b['t'] == 'img')))
