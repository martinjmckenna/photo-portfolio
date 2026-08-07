# Photographs

A hand-authored static photography portfolio. Plain HTML, CSS and vanilla JavaScript — no
build tools, no frameworks, no package manager, and no CDN-hosted libraries or fonts.
Every asset is served from the same origin.

Open `index.html` in a browser, or serve the directory over HTTP:

```sh
python3 -m http.server 8000
```

A server is worth using rather than `file://`, because cross-document view transitions and
some `<picture>` behaviour need a real origin.

## Layout

```
index.html      the grid                     (generated below the header)
404.html
styles.css      one stylesheet for the whole site
photo.js        swipe + arrow-key shortcuts, detail pages only
p/<slug>.html   one page per photograph      (generated)
img/            <slug>-{400,800,1600,3200}.{avif,webp,jpg}   (generated)
photos-src/     the original photographs, plus their captions
tools/          development-time helpers, not part of the site
notes.md        running log of decisions taken while building
```

## Adding or changing photographs

Put the originals in `photos-src/`, describe them in `photos-src/captions.txt`, and run
the importer:

```sh
python3 tools/import-photos.py                 # dry run — prints what it would do
python3 tools/import-photos.py --write --prune
```

It writes the AVIF / WebP / JPEG ladder into `img/`, writes one detail page per photograph
into `p/`, and rewrites the grid in `index.html` — including the `srcset` lists, the
`width`/`height` attributes, the per-photo `sizes`, the matching `view-transition-name`s
and the wrapping prev/next links. `--prune` deletes whatever is left over from the previous
run.

`img/`, `p/*.html` and the `<ul class="grid">` block in `index.html` are outputs. Don't
hand-edit them; the next run overwrites them. Everything else in the repository is
hand-authored, and the importer never touches it.

Ordering is filename order, so the source filenames set the running order — see
`photos-src/README.md` for naming, captions and the accepted formats.

Requires Pillow with AVIF and WebP support (`pip install Pillow`, version 12 or newer).
It is a development-time dependency: nothing is installed to serve the site, and the
published output is still plain hand-shaped HTML with no runtime build step.

## What the importer decides for you

- **The ladder** is 400 / 800 / 1600 / 3200, trimmed per photo to the widths at or below
  the source's own resolution — a small source is never upscaled to fill it. Tall crops are
  capped lower still, because a 9:16 photo letterboxed into any viewport is never displayed
  near 3200px wide.
- **`sizes` on the detail page** is `min(100vw, Nvh)`, where N is the photo's aspect ratio
  (width ÷ height) × 100 — a 3:2 photo is `150vh`. That second term is what stops the
  browser fetching a variant far wider than the letterbox can ever show.
- **The first tile** is `loading="eager"` + `fetchpriority="high"` as the likely LCP
  element; every other tile is lazy.
- **Colour** is converted to sRGB and **EXIF rotation** is applied on the way in, so an
  export from Lightroom or Photos arrives the right way up and the right colour.

## Placeholders

`tools/make-placeholders.py` renders the greyscale gradients that stood in before the real
photographs arrived. It is kept for regenerating a demo set from nothing; the importer is
what the site is built with now.
