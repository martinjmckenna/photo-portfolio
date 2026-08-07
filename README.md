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
photos-src/     captions, and originals *only while importing* — see below
tools/          development-time helpers, not part of the site
notes.md        running log of decisions taken while building
docs/           longer write-ups that outgrew the running log
```

## Adding or changing photographs

**Read this before running the importer.** It is a whole-collection build: whatever is in
`photos-src/` *is* the collection. Originals are deleted from the branch after each import,
so the folder normally holds only `captions.txt` — and running the importer against it in
that state builds a site with no photographs in it and, with `--prune`, deletes the ones
already published.

So the first step is always to put every original back:

```sh
git log --oneline -- photos-src            # find the commit holding the originals
git checkout <sha> -- photos-src/          # restore all of them
```

Then add or change what you came to add or change, describe it in `photos-src/captions.txt`,
and run:

```sh
python3 tools/import-photos.py                 # dry run — prints what it would do
python3 tools/import-photos.py --write --prune
```

**Check the photograph count in the dry-run summary before writing.** It prints e.g.
`8 photographs, 72 image files, 8 detail pages`. If that number is lower than the collection,
stop — the originals are not all present, and `--prune` would delete the difference.

Afterwards, take the originals back off the branch (`git rm` them, keeping `captions.txt`)
before committing. The Pages workflow uploads the repository as-is, so anything left in
`photos-src/` is published at a guessable URL — full-resolution, and carrying whatever
location data the camera wrote.

This is clumsy, and `docs/importer-and-incremental-updates.md` sets out the manifest-based
fix that removes the restore step entirely.

It writes the AVIF / WebP / JPEG ladder into `img/`, writes one detail page per photograph
into `p/`, and rewrites the grid in `index.html` — including the `srcset` lists, the
`width`/`height` attributes, the per-photo `sizes`, the matching `view-transition-name`s
and the wrapping prev/next links. `--prune` deletes whatever is left over from the previous
run.

`img/`, `p/*.html` and the `<ul class="grid">` block in `index.html` are outputs. Don't
hand-edit them; the next run overwrites them. Everything else in the repository is
hand-authored, and the importer never touches it.

Ordering is filename order, so the source filenames set the running order — see
`photos-src/README.md` for naming, captions and the accepted formats. Watch for
camera-assigned names: an `IMG_####.jpeg` sorts by where its letters fall in the alphabet,
not by when you added it, and the first photograph in the grid is also the eagerly-loaded
one. Rename before importing.

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

## The detail page

One control bar across the top — Index on the left, the counter and the two arrows grouped on
the right — and the photograph letterboxed into everything below it. The bar is a grid row
rather than a fixed overlay, so nothing is ever drawn on top of the picture at any viewport
size. `photo.js` adds swipe and arrow-key shortcuts to links that already exist in the
markup; with JavaScript off, the visible links work exactly as before.

## Placeholders

`tools/make-placeholders.py` renders the greyscale gradients that stood in before the real
photographs arrived. It is kept for regenerating a demo set from nothing; the importer is
what the site is built with now.

## Further reading

- `notes.md` — running log of every decision, newest last
- `docs/importer-and-incremental-updates.md` — why adding one photograph is currently hard,
  and the manifest-based fix
- `docs/landscape-experiment.md` — what a landscape frame does to the layout and the grid
