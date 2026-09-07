"""Re-encode the exhibits for embedding.

Every referenced image is inlined in the single-file deliverable, so raw PNGs
are out of the question — the extracted set is 48 MB. These are flat diagrams
and screenshots of tables, which WebP handles at a fraction of the size while
staying legible at the width the page actually renders them.
"""
import json, os
from PIL import Image

import paths

SRC = paths.DUMPIMG
OUT = paths.WEBP
os.makedirs(OUT, exist_ok=True)

parsed = json.load(open(paths.PARSED, encoding='utf-8'))

used = set()
for q in parsed['questions']:
    for key in ('body', 'ansimg', 'e'):
        for n in q[key]:
            if 'img' in n:
                used.add(n['img'])
for nodes in parsed['cases'].values():
    for n in nodes:
        if 'img' in n:
            used.add(n['img'])

# Every exhibit the dump carries is watermarked by the vendor. clean/ holds
# unwatermarked copies of the ones we have, mapped to the extracted filename
# they stand in for, so the substitution happens here and nothing downstream
# needs to know about it.
CLEAN_DIR = os.path.join(paths.HERE, 'clean')
overrides = {}
_ov = os.path.join(CLEAN_DIR, 'overrides.json')
if os.path.exists(_ov):
    overrides = json.load(open(_ov, encoding='utf-8')).get('images', {})

MAXW = 1000
total_src = total_out = 0
sizes = {}
for name in sorted(used):
    replacement = overrides.get(name)
    src = os.path.join(CLEAN_DIR, replacement) if replacement else os.path.join(SRC, name)
    total_src += os.path.getsize(src)
    im = Image.open(src)
    if im.mode not in ('RGB', 'L'):
        im = im.convert('RGB')
    if im.width > MAXW:
        im = im.resize((MAXW, round(im.height * MAXW / im.width)), Image.LANCZOS)
    dst = os.path.join(OUT, name.rsplit('.', 1)[0] + '.webp')  # keyed by the extracted name
    im.save(dst, quality=80, method=6)
    n = os.path.getsize(dst)
    total_out += n
    sizes[name] = (os.path.basename(dst), n, im.width, im.height)

json.dump(sizes, open(paths.IMGMAP, 'w', encoding='utf-8'), indent=1)
print('referenced images: %d' % len(used))
print('source  %.1f MB' % (total_src / 1e6))
print('webp    %.2f MB  (base64 approx %.2f MB)' % (total_out / 1e6, total_out * 4 / 3 / 1e6))
big = sorted(sizes.items(), key=lambda kv: -kv[1][1])[:5]
print('largest:', [(k, '%d KB' % (v[1] // 1024)) for k, v in big])
if overrides:
    print('clean replacements used: %d (%s)'
          % (len(overrides), ', '.join(sorted(overrides.values()))))
