# Build notes

Running log of what got built, decisions taken, and things deliberately left for later.
Newest entries at the bottom.

---

## 1. Skeleton

- `index.html` — bare page shell: `<meta viewport>` with no `user-scalable=no` and no
  `maximum-scale` (native pinch-to-zoom is a V2 requirement that costs nothing as long as
  nothing disables it), a stylesheet link, a site title, and an empty `.grid`.
- No build tooling, no package manager, no dependencies. Everything is hand-authored and
  served from the same origin, per the spec.

## 2. Placeholder imagery

Real photographs land later, so `tools/make-placeholders.py` renders nine greyscale
gradients to stand in for them. It is a development-time script, not part of the site —
nothing in `img/` is hand-maintained and the whole directory is disposable.

- Each master is a smoothstepped gradient (linear / radial / angular sweep) with a vignette
  and a light grain pass. The grain matters for two reasons: it dithers away the 8-bit
  banding a pure gradient would show, and it gives the three encoders something realistic
  to chew on rather than a best-case synthetic image.
- Deliberately mixed aspect ratios — 3:2, 2:3, 1:1, 16:9, 4:5, 5:4, 9:16 — so both the 4:5
  `object-fit: cover` crop on the grid and the letterboxing on the detail page are visible
  under real conditions rather than only with conveniently-shaped images.
- Formats: AVIF, WebP and JPEG at each width, per the spec's `<picture>` layering.
- Resolution ladder is 400/800/1600/3200, but trimmed per photo to widths at or below the
  master width. Tall crops get a smaller master (a 9:16 photo letterboxed into any viewport
  is never displayed near 3200px wide, so that variant would be pure waste). A real build
  script should do the same rather than upscaling a source file to fill the ladder.
- Total output is ~7MB across 93 files.

## 3. Homepage grid and stylesheet

`index.html` is now the real grid: nine tiles in document order, each an `<a>` wrapping a
`<picture>` with AVIF → WebP → JPEG sources and a width-descriptor `srcset`.

- **Column floor.** The spec suggests 240px; I went with 220px after checking the numbers at
  common widths. It lands 1 column at 390px, 3 at 768px, 5 at 1440px — 240px would have
  given only 2 columns at tablet width, which felt sparse. Written as
  `minmax(min(220px, 100%), 1fr)`: the `min()` stops a single column from overflowing very
  narrow viewports where 220px plus page padding exceeds the available width. This is still
  the one knob worth re-checking once real photographs are in.
- **Grid `sizes`.** `(max-width: 599px) calc(100vw - 2rem), 440px` — below 600px a tile is
  the full viewport minus page padding; above it, 440px is the widest a column can get
  before `auto-fill` adds another one.
- **First tile** is `loading="eager"` + `fetchpriority="high"` as the likely LCP element;
  everything else is `loading="lazy"`.
- **Colour.** Dark by default with a light-mode inversion via `prefers-color-scheme`, all of
  it black/white/grey. Hover feedback has to be tonal rather than chromatic on a monochrome
  site, so it is a 2% scale lift plus an opacity dip, gated behind `@media (hover: hover)`
  so it does not stick after a tap on touch devices.
- **Fonts** are the OS stack — nothing is downloaded.

The stylesheet also lays down the detail-page and 404 rules in the same file; those pages
arrive in the next commits. One stylesheet for the whole site keeps the request count at one
and is small enough not to warrant splitting.
