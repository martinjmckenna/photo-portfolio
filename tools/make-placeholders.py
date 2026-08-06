#!/usr/bin/env python3
"""Generate greyscale gradient stand-ins for the real photographs.

Development-time only — nothing here ships to the browser, and the whole
`img/` directory it writes is meant to be deleted once real photos arrive.

For each photo in PHOTOS it renders a master image (a smooth greyscale
gradient with a vignette and a little grain so it reads as a photograph
rather than a CSS background) and then writes the AVIF / WebP / JPEG
variants at each width in the resolution ladder.

    python3 tools/make-placeholders.py

Requires Pillow with AVIF and WebP support (Pillow >= 12).
"""

import math
import os
from PIL import Image, ImageChops, ImageFilter

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "img")

# The full ladder from the spec. Per-photo it is trimmed to the widths that
# are actually <= the master width, which is what a real build script would
# do rather than upscaling a source file.
LADDER = [400, 800, 1600, 3200]

# Master width per photo. Tall crops get a smaller master on purpose: a 9:16
# photo letterboxed into a landscape viewport is never displayed anywhere near
# 3200px wide, so generating that variant would only waste bytes.
MASTER_WIDTH = {
    "landscape": 3200,
    "square": 2600,
    "portrait": 2000,
    "tall": 1600,
}

QUALITY = {"jpg": 78, "webp": 76, "avif": 58}

# slug, (aspect w, aspect h), size class, gradient recipe
PHOTOS = [
    ("demo-01", (3, 2), "landscape", ("linear", 90, [(0.0, 232), (0.55, 150), (1.0, 44)])),
    ("demo-02", (2, 3), "portrait", ("linear", 35, [(0.0, 28), (0.5, 120), (1.0, 238)])),
    ("demo-03", (1, 1), "square", ("radial", (0.5, 0.45), [(0.0, 244), (0.6, 128), (1.0, 22)])),
    ("demo-04", (16, 9), "landscape", ("linear", 0, [(0.0, 30), (0.42, 210), (1.0, 56)])),
    ("demo-05", (4, 5), "portrait", ("radial", (0.72, 0.28), [(0.0, 250), (0.45, 118), (1.0, 34)])),
    ("demo-06", (3, 2), "landscape", ("linear", 90, [(0.0, 38), (0.4, 96), (1.0, 226)])),
    ("demo-07", (2, 3), "portrait", ("sweep", 0.15, [(0.0, 18), (0.35, 176), (0.7, 72), (1.0, 214)])),
    ("demo-08", (5, 4), "landscape", ("radial", (0.35, 0.6), [(0.0, 206), (0.35, 158), (1.0, 16)])),
    ("demo-09", (9, 16), "tall", ("linear", 125, [(0.0, 210), (0.3, 62), (0.62, 190), (1.0, 40)])),
]


def sample(stops, t):
    """Linear interpolation through a list of (position, 0-255) stops."""
    t = min(1.0, max(0.0, t))
    for i in range(len(stops) - 1):
        p0, v0 = stops[i]
        p1, v1 = stops[i + 1]
        if p0 <= t <= p1:
            span = p1 - p0
            k = 0.0 if span == 0 else (t - p0) / span
            # Smoothstep between stops so the joins do not show as hard creases.
            k = k * k * (3 - 2 * k)
            return v0 + (v1 - v0) * k
    return stops[-1][1]


def render_gradient(recipe, w, h):
    """Render the gradient small, then scale up — cheap and perfectly smooth."""
    kind = recipe[0]
    sw = 360
    sh = max(1, round(sw * h / w))
    px = []

    if kind == "linear":
        angle = math.radians(recipe[1])
        dx, dy = math.cos(angle), math.sin(angle)
        # Normalise so the projection spans 0..1 across the whole image.
        extent = abs(dx) + abs(dy)
        for y in range(sh):
            v = (y + 0.5) / sh
            for x in range(sw):
                u = (x + 0.5) / sw
                t = (u * dx + v * dy + (1 if dx < 0 else 0) + (1 if dy < 0 else 0)) / extent
                px.append(int(sample(recipe[2], t)))

    elif kind == "radial":
        cx, cy = recipe[1]
        for y in range(sh):
            v = (y + 0.5) / sh
            for x in range(sw):
                u = (x + 0.5) / sw
                # Scale x by the aspect ratio so the falloff stays circular.
                d = math.hypot((u - cx) * (w / h), v - cy) / 1.05
                px.append(int(sample(recipe[2], d)))

    elif kind == "sweep":
        offset = recipe[1]
        for y in range(sh):
            v = (y + 0.5) / sh
            for x in range(sw):
                u = (x + 0.5) / sw
                t = (math.atan2(v - 0.5, u - 0.5) / math.pi + 1) / 2
                px.append(int(sample(recipe[2], (t + offset) % 1.0)))

    else:
        raise ValueError("unknown gradient kind: %r" % kind)

    small = Image.new("L", (sw, sh))
    small.putdata(px)
    small = small.filter(ImageFilter.GaussianBlur(2))
    return small.resize((w, h), Image.BICUBIC)


def vignette(w, h):
    sw, sh = 240, max(1, round(240 * h / w))
    px = []
    for y in range(sh):
        v = (y + 0.5) / sh
        for x in range(sw):
            u = (x + 0.5) / sw
            d = math.hypot(u - 0.5, v - 0.5) / 0.72
            px.append(int(255 - 70 * min(1.0, max(0.0, d)) ** 2.2))
    mask = Image.new("L", (sw, sh))
    mask.putdata(px)
    return mask.resize((w, h), Image.BICUBIC)


def render_master(recipe, w, h):
    img = render_gradient(recipe, w, h)
    img = ImageChops.multiply(img, vignette(w, h))
    # Fine grain, kept subtle: enough to dither 8-bit banding without reading
    # as noise, and enough texture that the compressors get a realistic workout.
    grain = Image.effect_noise((w, h), 5).filter(ImageFilter.GaussianBlur(0.4))
    img = ImageChops.add(img, grain, scale=1.0, offset=-128)
    return img.convert("RGB")


def variants(slug, master, master_w):
    widths = [w for w in LADDER if w <= master_w] or [master_w]
    written = []
    for width in widths:
        height = round(master.height * width / master.width)
        resized = master.resize((width, height), Image.LANCZOS)
        base = os.path.join(OUT_DIR, f"{slug}-{width}")
        resized.save(base + ".jpg", quality=QUALITY["jpg"], optimize=True, progressive=True)
        resized.save(base + ".webp", quality=QUALITY["webp"], method=6)
        resized.save(base + ".avif", quality=QUALITY["avif"])
        written.append((width, height))
    return written


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for slug, (aw, ah), size_class, recipe in PHOTOS:
        w = MASTER_WIDTH[size_class]
        h = round(w * ah / aw)
        master = render_master(recipe, w, h)
        written = variants(slug, master, w)
        print(f"{slug}  {aw}:{ah}  master {w}x{h}  ->  " + ", ".join(f"{a}x{b}" for a, b in written))


if __name__ == "__main__":
    main()
