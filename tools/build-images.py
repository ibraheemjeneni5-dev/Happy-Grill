#!/usr/bin/env python
"""
Happy Grill — image build step.

Converts the source photos in assets/ to WebP, capped at roughly twice the size
they are actually displayed at, and writes the results to assets/webp/.

The originals are left untouched: they are the masters, and nothing on the page
loads them any more. Re-run this after replacing or adding a photo:

    python tools/build-images.py

Requires Pillow:  python -m pip install --user Pillow
"""

import os
import sys
from collections import deque

from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets")
OUT = os.path.join(SRC, "webp")

# Longest edge to keep, per role. Roughly 2x the CSS size the photo is drawn at,
# so it stays sharp on a retina phone without shipping a poster-sized file.
# Nothing is ever upscaled — a source smaller than its cap is left as-is.
HERO = 900   # hero slideshow: 430px frame, plus the slow zoom, on a 2x screen
DISH = 520   # menu thumbnail at 132px, and the same file again in the dish modal
CAN = 420   # drinks fridge: 104px tall bottle on a 2x screen
MARK = 96   # logo in the top bar: 34px square

def knock_out_white(im, threshold=232):
    """Make a photo's white studio backdrop transparent.

    Only the background is removed: the fill starts from the border and stops at
    the first pixel that isn't near-white, so a white highlight *inside* the food
    is never punched through. The resulting edge is blurred by half a pixel so it
    doesn't read as a cut-out sticker against a dark card.
    """
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()

    def is_backdrop(x, y):
        r, g, b, _ = px[x, y]
        return r >= threshold and g >= threshold and b >= threshold

    mask = Image.new("L", (w, h), 255)   # 255 = keep
    mp = mask.load()
    seen = bytearray(w * h)
    queue = deque()

    for x in range(w):
        for y in (0, h - 1):
            if not seen[y * w + x] and is_backdrop(x, y):
                seen[y * w + x] = 1
                queue.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if not seen[y * w + x] and is_backdrop(x, y):
                seen[y * w + x] = 1
                queue.append((x, y))

    while queue:
        x, y = queue.popleft()
        mp[x, y] = 0
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and is_backdrop(nx, ny):
                seen[ny * w + nx] = 1
                queue.append((nx, ny))

    mask = mask.filter(ImageFilter.GaussianBlur(0.5))
    im.putalpha(mask)
    return im


PLAN = [
    # (filename, cap, quality)
    # -- used by both the hero slideshow and a menu card, so kept at hero size --
    ("chicken-burger.png", HERO, 82),
    ("kebab.png",          HERO, 82),
    ("HappySalad.png",     HERO, 82),
    ("burger.jpg",         HERO, 84),
    ("taouk.jpg",          HERO, 84),
    ("falafel.jpg",        HERO, 84),
    # -- menu thumbnails only --
    ("Patty.png",          DISH, 82),
    ("fries.jpg",          DISH, 82),
    ("friesmix.png",       DISH, 82),
    ("cheese.jpg",         DISH, 84),
    ("onionsmush.png",     DISH, 82),
    # -- drinks --
    ("cola.png",           CAN, 82),
    ("cola-zero.png",      CAN, 82),
    ("sprite.png",         CAN, 82),
    ("fanta.png",          CAN, 82),
    ("xl.png",             CAN, 82),
    ("blu.png",            CAN, 82),
    ("Water.png",          CAN, 82),
    # -- brand --
    ("logo.jpg",           MARK, 86),
]

# Shot on a white studio backdrop, but shown on a dark card with object-fit:contain.
# Without this the photo reads as a white box floating in the card.
CUTOUT = {"Patty.png"}


def build(name, cap, quality):
    src = os.path.join(SRC, name)
    if not os.path.exists(src):
        print("  skip (missing): %s" % name)
        return None

    im = Image.open(src)
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    im = im.convert("RGBA" if has_alpha else "RGB")

    before = im.size
    if name in CUTOUT:
        im = knock_out_white(im)
    if max(im.size) > cap:
        im.thumbnail((cap, cap), Image.LANCZOS)

    dest = os.path.join(OUT, os.path.splitext(name)[0] + ".webp")
    im.save(dest, "WEBP", quality=quality, method=6)

    old_kb = os.path.getsize(src) / 1024.0
    new_kb = os.path.getsize(dest) / 1024.0
    print("  %-22s %sx%s -> %sx%s   %6.0f KB -> %5.0f KB  (-%.0f%%)" % (
        name, before[0], before[1], im.size[0], im.size[1],
        old_kb, new_kb, (1 - new_kb / old_kb) * 100))
    return old_kb, new_kb, im.size


def main():
    if not os.path.isdir(SRC):
        sys.exit("assets/ not found next to tools/")
    if not os.path.isdir(OUT):
        os.makedirs(OUT)

    print("Building WebP into assets/webp/ ...")
    total_old = total_new = 0.0
    sizes = {}
    for name, cap, quality in PLAN:
        result = build(name, cap, quality)
        if result:
            old_kb, new_kb, dim = result
            total_old += old_kb
            total_new += new_kb
            sizes[os.path.splitext(name)[0] + ".webp"] = dim

    print("\n  total  %.0f KB -> %.0f KB  (-%.0f%%)" % (
        total_old, total_new, (1 - total_new / total_old) * 100))

    # Printed so the width/height attributes in index.html can be kept honest.
    print("\nIntrinsic sizes for the HTML width/height attributes:")
    for f in sorted(sizes):
        print("  %-24s width=\"%s\" height=\"%s\"" % (f, sizes[f][0], sizes[f][1]))


if __name__ == "__main__":
    main()
