#!/usr/bin/env python
"""
Happy Grill — cheddar slice art.

The original cheddar photo was a soft 320px JPEG: out of focus at the source, so
no amount of resizing made it sharp. This draws the slices instead — a fanned
stack rendered as vector shapes at 4x and downsampled, so the edges stay crisp
at every screen density, on the same dark card background as the other dishes.

    python tools/make-cheese.py

Requires Pillow:  python -m pip install --user Pillow
"""

import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "webp", "cheese.webp")

SIZE = 520          # matches the DISH cap in build-images.py
SS = 4              # supersampling factor
S = SIZE * SS

COAL = (20, 16, 9)           # --coal, the card background
SQUASH = 0.56                # vertical foreshortening: we look down at the plate
THICK = 0.030 * S            # slice thickness in px


def quad(cx, cy, half, angle, squash=SQUASH):
    """A square slice of side 2*half, rotated then flattened into perspective."""
    a = math.radians(angle)
    pts = []
    for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x, y = dx * half, dy * half
        rx = x * math.cos(a) - y * math.sin(a)
        ry = x * math.sin(a) + y * math.cos(a)
        pts.append((cx + rx, cy + ry * squash))
    return pts


def shift(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


def lerp(c1, c2, t):
    return tuple(int(round(a + (b - a) * t)) for a, b in zip(c1, c2))


def gradient_fill(size, top, bottom, angle_tilt=0.35):
    """Vertical gradient with a slight diagonal lean, so the light has a source."""
    w, h = size
    grad = Image.new("RGB", (w, h))
    px = grad.load()
    for y in range(h):
        for x in range(w):
            t = (y / (h - 1)) * (1 - angle_tilt) + (x / (w - 1)) * angle_tilt
            px[x, y] = lerp(top, bottom, min(1.0, max(0.0, t)))
    return grad


def speckle(layer, pts, seed):
    """The faint darker flecks that keep a flat orange from reading as plastic."""
    rnd = random.Random(seed)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    d = ImageDraw.Draw(layer, "RGBA")
    for _ in range(90):
        x = rnd.uniform(min(xs), max(xs))
        y = rnd.uniform(min(ys), max(ys))
        r = rnd.uniform(1.2, 3.4) * SS
        dark = rnd.random() < 0.65
        col = (150, 78, 8, rnd.randint(26, 54)) if dark else (255, 214, 150, rnd.randint(20, 44))
        d.ellipse((x - r, y - r, x + r, y + r), fill=col)


def draw_slice(base, pts, top_a, top_b, seed):
    """One slice: cast shadow, extruded edge, gradient top face, rim light."""
    # cast shadow on the slices below
    shadow = Image.new("L", (S, S), 0)
    ImageDraw.Draw(shadow).polygon(shift(pts, 0.012 * S, 0.030 * S), fill=150)
    shadow = shadow.filter(ImageFilter.GaussianBlur(0.020 * S))
    base.paste(Image.new("RGB", (S, S), (8, 5, 2)), (0, 0), shadow)

    # extruded side, drawn as the top face swept downwards
    side = ImageDraw.Draw(base, "RGBA")
    for i in range(int(THICK), 0, -1):
        t = i / THICK
        side.polygon(shift(pts, 0, i), fill=lerp((116, 55, 6), (198, 104, 14), 1 - t))

    # top face
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(0.6 * SS))   # anti-aliased edge
    face = gradient_fill((S, S), top_a, top_b)
    speckle_layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    speckle(speckle_layer, pts, seed)
    face = face.convert("RGBA")
    face.alpha_composite(speckle_layer)
    base.paste(face.convert("RGB"), (0, 0), mask)

    # rim light along the two upper edges, then a soft darkening on the lower two
    rim = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim)
    rd.line([pts[0], pts[1]], fill=(255, 226, 168, 150), width=int(0.005 * S))
    rd.line([pts[0], pts[3]], fill=(255, 216, 150, 110), width=int(0.004 * S))
    rim = rim.filter(ImageFilter.GaussianBlur(1.1 * SS))
    base.paste(rim.convert("RGB"), (0, 0), rim.split()[3])


def main():
    base = Image.new("RGB", (S, S), COAL)

    # a warm pool of light under the stack, so the slices sit on the card
    glow = Image.new("L", (S, S), 0)
    ImageDraw.Draw(glow).ellipse(
        (0.10 * S, 0.42 * S, 0.90 * S, 0.90 * S), fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(0.09 * S))
    base.paste(Image.new("RGB", (S, S), (86, 44, 12)), (0, 0), glow)

    half = 0.205 * S
    # back to front, fanned so every corner stays inside the 132px card crop
    layout = [
        (0.585 * S, 0.470 * S, half * 1.00, -24, (255, 174, 72), (224, 124, 22), 11),
        (0.395 * S, 0.520 * S, half * 1.02, 20, (255, 181, 80), (230, 131, 24), 23),
        (0.585 * S, 0.585 * S, half * 0.98, 6, (255, 186, 90), (236, 138, 26), 37),
        (0.455 * S, 0.435 * S, half * 0.94, -7, (255, 200, 110), (243, 151, 34), 51),
    ]
    for cx, cy, h, ang, top_a, top_b, seed in layout:
        draw_slice(base, quad(cx, cy, h, ang), top_a, top_b, seed)

    out = base.resize((SIZE, SIZE), Image.LANCZOS)
    out.save(OUT, "WEBP", quality=88, method=6)
    print("wrote %s  %sx%s  %.0f KB" % (
        os.path.relpath(OUT, ROOT), SIZE, SIZE, os.path.getsize(OUT) / 1024.0))


if __name__ == "__main__":
    main()
