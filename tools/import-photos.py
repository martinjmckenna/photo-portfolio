#!/usr/bin/env python3
"""Turn a folder of photographs into the site.

Development-time only — nothing here ships to the browser. It reads the
originals out of `photos-src/`, writes the AVIF / WebP / JPEG ladder into
`img/`, and regenerates the grid in `index.html` plus one detail page per
photograph in `p/`.

    python3 tools/import-photos.py                    # dry run summary first
    python3 tools/import-photos.py --write            # actually write
    python3 tools/import-photos.py --write --prune    # and delete stale files

This is the script the README describes as the eventual replacement for
hand-editing three files per photograph: given one high-resolution source per
photo plus an ordering, it emits the variants, the `<picture>` markup and the
prev/next links. `img/` and `p/` are outputs — do not hand-edit them, the next
run overwrites whatever is there.

Ordering is filename order by default, which makes the source filenames the
running order: prefix them `01-`, `02-` and so on to arrange the grid. Pass
`--order exif` to sequence by capture time instead.

Alt text comes from `photos-src/captions.txt`, one photo per line:

    01-harbour-wall.jpg | Wet harbour wall, the tide out, ropes coiled at the edge.

Blank lines and `#` comments are ignored. The key is the source filename (with
or without its extension). Any photo without a caption still gets written, with
alt text derived from its filename and a warning at the end of the run — that
derived text is a placeholder, not a description, and should be replaced.

Requires Pillow with AVIF and WebP support (Pillow >= 12).
"""

import argparse
import datetime
import html
import io
import os
import re
import sys

try:
    from PIL import Image, ImageCms, ImageOps
except ImportError:
    sys.exit("Pillow is not installed. Try: pip install Pillow")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "photos-src")
IMG_DIR = os.path.join(ROOT, "img")
PAGE_DIR = os.path.join(ROOT, "p")
INDEX = os.path.join(ROOT, "index.html")

SOURCE_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".avif", ".heic", ".heif"}

# The resolution ladder, trimmed per photo to the widths at or below that
# photo's master width — never upscale a source to fill the ladder.
LADDER = [400, 800, 1600, 3200]

# Master width cap per aspect class. A tall crop letterboxed into any viewport
# is never displayed near 3200px wide, so that variant would be pure waste.
# Matches the reasoning in tools/make-placeholders.py.
MASTER_CAP = [
    # (minimum width/height ratio, cap)
    (1.2, 3200),   # landscape
    (0.9, 2600),   # square-ish
    (0.7, 2000),   # portrait
    (0.0, 1600),   # tall
]

QUALITY = {"jpg": 78, "webp": 76, "avif": 58}

GRID_SIZES = "(max-width: 599px) calc(100vw - 2rem), 440px"

# The <img> that the browser falls back to when it understands neither AVIF nor
# WebP, and the width it should aim for on each page type.
GRID_FALLBACK_WIDTH = 800
PAGE_FALLBACK_WIDTH = 1600


# --- Sources ----------------------------------------------------------------


def slugify(stem):
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return slug or "photo"


def humanise(stem):
    """A last-resort alt text from a filename. Deliberately obviously a stand-in."""
    words = re.sub(r"[^a-z0-9]+", " ", stem.lower()).strip()
    words = re.sub(r"^\d+\s+", "", words)  # drop a leading ordering prefix
    return words.capitalize() if words else "Photograph"


def read_captions(path):
    """`filename | alt text` per line. Keyed by filename and by bare stem."""
    captions = {}
    if not os.path.exists(path):
        return captions

    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # `|` first, then tab, then the first colon — whichever the author used.
            for sep in ("|", "\t"):
                if sep in line:
                    name, _, alt = line.partition(sep)
                    break
            else:
                name, _, alt = line.partition(":")
            name, alt = name.strip(), alt.strip()
            if not name or not alt:
                print(f"  ! captions.txt line {lineno}: no separator, ignored", file=sys.stderr)
                continue
            captions[name] = alt
            captions[os.path.splitext(name)[0]] = alt
    return captions


def capture_time(img, path):
    exif = img.getexif()
    # 36867 DateTimeOriginal, 306 DateTime
    for tag in (36867, 306):
        value = exif.get(tag)
        if value:
            try:
                return datetime.datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
            except ValueError:
                pass
    return datetime.datetime.fromtimestamp(os.path.getmtime(path))


def discover(src_dir, order):
    if not os.path.isdir(src_dir):
        sys.exit(f"No source folder at {src_dir} — create it and put the photographs in it.")

    files = [
        os.path.join(src_dir, name)
        for name in os.listdir(src_dir)
        if os.path.splitext(name)[1].lower() in SOURCE_EXT and not name.startswith(".")
    ]
    if not files:
        sys.exit(f"No images found in {src_dir} (looked for: {', '.join(sorted(SOURCE_EXT))})")

    if order == "exif":
        keyed = []
        for path in files:
            with Image.open(path) as img:
                keyed.append((capture_time(img, path), path))
        keyed.sort()
        return [path for _, path in keyed]

    # Natural sort, so `10-foo` follows `9-foo` rather than `1-foo`.
    def natural(path):
        name = os.path.basename(path).lower()
        return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", name)]

    return sorted(files, key=natural)


# --- Image processing -------------------------------------------------------


SRGB = ImageCms.createProfile("sRGB")


def load(path, grayscale):
    """Open, straighten, and normalise to 8-bit sRGB."""
    img = Image.open(path)
    # Rotate per the EXIF orientation flag and drop the flag, so the pixels are
    # the right way up for encoders that ignore it.
    img = ImageOps.exif_transpose(img)

    icc = img.info.get("icc_profile")
    if icc:
        # A photo exported in Adobe RGB or Display P3 renders desaturated in
        # browsers if the profile is dropped without converting. Convert to
        # sRGB rather than embedding the profile in every variant.
        try:
            src = ImageCms.getOpenProfile(io.BytesIO(icc))
            img = ImageCms.profileToProfile(img, src, SRGB, outputMode="RGB")
        except (ImageCms.PyCMSError, OSError):
            img = img.convert("RGB")
    else:
        img = img.convert("RGB")

    if grayscale:
        img = ImageOps.grayscale(img).convert("RGB")

    return img


def master_cap(width, height):
    ratio = width / height
    for floor, cap in MASTER_CAP:
        if ratio >= floor:
            return cap
    return MASTER_CAP[-1][1]


def widths_for(width, height):
    cap = min(width, master_cap(width, height))
    widths = [w for w in LADDER if w <= cap]
    return widths or [cap]


def encode(img, slug, widths, out_dir, write):
    """Write every variant. Returns [(width, height)] in ladder order."""
    written = []
    for width in widths:
        height = max(1, round(img.height * width / img.width))
        if write:
            resized = img.resize((width, height), Image.LANCZOS)
            base = os.path.join(out_dir, f"{slug}-{width}")
            resized.save(base + ".jpg", quality=QUALITY["jpg"], optimize=True, progressive=True)
            resized.save(base + ".webp", quality=QUALITY["webp"], method=6)
            resized.save(base + ".avif", quality=QUALITY["avif"])
        written.append((width, height))
    return written


# --- Markup -----------------------------------------------------------------


def srcset(slug, variants, ext, prefix):
    return ", ".join(f"{prefix}{slug}-{w}.{ext} {w}w" for w, _ in variants)


def nearest(variants, target):
    """The variant closest to `target`, never exceeding it unless all do."""
    at_or_below = [w for w, _ in variants if w <= target]
    return max(at_or_below) if at_or_below else min(w for w, _ in variants)


def grid_tile(photo, first):
    slug, alt, variants = photo["slug"], photo["alt"], photo["variants"]
    fallback = nearest(variants, GRID_FALLBACK_WIDTH)
    # The grid crops every tile to 4:5, but the intrinsic ratio still belongs on
    # the element: it is what reserves the right box before the image lands.
    tile_w = GRID_FALLBACK_WIDTH
    tile_h = round(tile_w * photo["height"] / photo["width"])
    loading = (
        'loading="eager" fetchpriority="high"' if first else 'loading="lazy"'
    )
    esc = html.escape(alt, quote=True)

    return f"""    <li>
      <a class="tile" id="{slug}" href="p/{slug}.html">
        <picture>
          <source type="image/avif" sizes="{GRID_SIZES}"
            srcset="{srcset(slug, variants, 'avif', 'img/')}">
          <source type="image/webp" sizes="{GRID_SIZES}"
            srcset="{srcset(slug, variants, 'webp', 'img/')}">
          <img src="img/{slug}-{fallback}.jpg"
            sizes="{GRID_SIZES}"
            srcset="{srcset(slug, variants, 'jpg', 'img/')}"
            width="{tile_w}" height="{tile_h}" {loading} decoding="async"
            style="view-transition-name: photo-{slug}"
            alt="{esc}">
        </picture>
      </a>
    </li>"""


def detail_page(photo, position, total, prev_slug, next_slug):
    slug, alt, variants = photo["slug"], photo["alt"], photo["variants"]
    fallback = nearest(variants, PAGE_FALLBACK_WIDTH)
    intrinsic_w, intrinsic_h = variants[-1]

    # The photo is letterboxed to fit, so its displayed width is capped by the
    # viewport height times its own aspect ratio. Telling `sizes` that keeps the
    # browser from picking a variant far wider than can ever be shown.
    vh = round(photo["width"] / photo["height"] * 100)
    sizes = f"min(100vw, {vh}vh)"
    esc = html.escape(alt, quote=True)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Photograph {position} of {total} — Photographs</title>
<meta name="description" content="{esc}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%23111'/%3E%3Ccircle cx='16' cy='16' r='7' fill='%23f2f2f2'/%3E%3C/svg%3E">
<link rel="stylesheet" href="../styles.css">
</head>
<body class="photo-page">

<picture>
  <source type="image/avif" sizes="{sizes}" srcset="{srcset(slug, variants, 'avif', '../img/')}">
  <source type="image/webp" sizes="{sizes}" srcset="{srcset(slug, variants, 'webp', '../img/')}">
  <img src="../img/{slug}-{fallback}.jpg"
    sizes="{sizes}"
    srcset="{srcset(slug, variants, 'jpg', '../img/')}"
    width="{intrinsic_w}" height="{intrinsic_h}" fetchpriority="high" decoding="async"
    style="view-transition-name: photo-{slug}"
    alt="{esc}">
</picture>

<nav class="photo-nav">
  <a class="nav-index" href="../index.html#{slug}">Index</a>
  <span class="counter" aria-hidden="true">{position}&#8202;/&#8202;{total}</span>
  <a class="nav-prev" rel="prev" href="{prev_slug}.html"><span aria-hidden="true">&#8592;</span> Prev</a>
  <a class="nav-next" rel="next" href="{next_slug}.html">Next <span aria-hidden="true">&#8594;</span></a>
</nav>

<script src="../photo.js" defer></script>
</body>
</html>
"""


def rewrite_index(photos, write):
    with open(INDEX, encoding="utf-8") as fh:
        source = fh.read()

    match = re.search(r'( *<ul class="grid">\n)(.*?)(\n *</ul>)', source, re.S)
    if not match:
        sys.exit("Could not find the <ul class=\"grid\"> block in index.html")

    tiles = "\n\n".join(grid_tile(p, i == 0) for i, p in enumerate(photos))
    updated = source[: match.start(2)] + "\n" + tiles + "\n" + source[match.end(2) :]

    if write:
        with open(INDEX, "w", encoding="utf-8") as fh:
            fh.write(updated)
    return updated != source


# --- Housekeeping -----------------------------------------------------------


def stale_files(photos):
    """Files in img/ and p/ that this run did not produce."""
    expected_img = {
        f"{p['slug']}-{w}.{ext}"
        for p in photos
        for w, _ in p["variants"]
        for ext in ("jpg", "webp", "avif")
    }
    expected_pages = {f"{p['slug']}.html" for p in photos}

    stale = []
    for name in sorted(os.listdir(IMG_DIR)) if os.path.isdir(IMG_DIR) else []:
        if name not in expected_img and not name.startswith("."):
            stale.append(os.path.join(IMG_DIR, name))
    for name in sorted(os.listdir(PAGE_DIR)) if os.path.isdir(PAGE_DIR) else []:
        if name not in expected_pages and not name.startswith("."):
            stale.append(os.path.join(PAGE_DIR, name))
    return stale


# --- Entry point ------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", nargs="?", default=SRC_DIR, help="folder of originals (default: photos-src/)")
    ap.add_argument("--write", action="store_true", help="write files; without it this is a dry run")
    ap.add_argument("--prune", action="store_true", help="delete files in img/ and p/ this run did not produce")
    ap.add_argument("--order", choices=("filename", "exif"), default="filename", help="grid order")
    ap.add_argument("--grayscale", action="store_true", help="convert to greyscale on the way in")
    ap.add_argument("--limit", type=int, help="process only the first N photographs")
    args = ap.parse_args()

    paths = discover(args.source, args.order)
    if args.limit:
        paths = paths[: args.limit]

    captions = read_captions(os.path.join(args.source, "captions.txt"))

    if args.write:
        os.makedirs(IMG_DIR, exist_ok=True)
        os.makedirs(PAGE_DIR, exist_ok=True)

    photos = []
    seen = set()
    missing_alt = []

    for path in paths:
        name = os.path.basename(path)
        stem = os.path.splitext(name)[0]

        slug = slugify(stem)
        n = 2
        while slug in seen:
            slug = f"{slugify(stem)}-{n}"
            n += 1
        seen.add(slug)

        img = load(path, args.grayscale)
        widths = widths_for(img.width, img.height)
        variants = encode(img, slug, widths, IMG_DIR, args.write)

        alt = captions.get(name) or captions.get(stem)
        if not alt:
            alt = humanise(stem)
            missing_alt.append((name, alt))

        photos.append(
            {
                "slug": slug,
                "alt": alt,
                "width": img.width,
                "height": img.height,
                "variants": variants,
                "source": name,
            }
        )
        img.close()

        ladder = ", ".join(f"{w}x{h}" for w, h in variants)
        print(f"{name}  ->  {slug}  {img.width}x{img.height}  ->  {ladder}")

    total = len(photos)
    for i, photo in enumerate(photos):
        page = detail_page(
            photo,
            i + 1,
            total,
            photos[(i - 1) % total]["slug"],
            photos[(i + 1) % total]["slug"],
        )
        if args.write:
            with open(os.path.join(PAGE_DIR, photo["slug"] + ".html"), "w", encoding="utf-8") as fh:
                fh.write(page)

    changed = rewrite_index(photos, args.write)

    print(f"\n{total} photograph{'s' if total != 1 else ''}, "
          f"{sum(len(p['variants']) for p in photos) * 3} image files, "
          f"{total} detail page{'s' if total != 1 else ''}"
          f"{'' if changed else ' (index.html unchanged)'}")

    stale = stale_files(photos)
    if stale:
        print(f"\n{len(stale)} stale file(s) left over from a previous run:")
        for path in stale[:12]:
            print(f"  {os.path.relpath(path, ROOT)}")
        if len(stale) > 12:
            print(f"  ... and {len(stale) - 12} more")
        if args.prune and args.write:
            for path in stale:
                os.remove(path)
            print("  deleted (--prune)")
        else:
            print("  re-run with --write --prune to delete them")

    if missing_alt:
        print(f"\n{len(missing_alt)} photograph(s) have no caption. Placeholder alt text was")
        print("written from the filename — add real descriptions to photos-src/captions.txt:")
        for name, alt in missing_alt:
            print(f"  {name} | {alt}")

    if not args.write:
        print("\nDry run — nothing was written. Re-run with --write.")


if __name__ == "__main__":
    main()
