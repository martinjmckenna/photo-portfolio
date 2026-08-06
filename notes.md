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

## 4. Photo detail pages

Nine pages under `p/`, one per photograph. They were emitted once from a throwaway
scaffold so nine near-identical files would not have to be typed out by hand; the files
themselves are now the source of truth and are meant to be edited directly. No build step
exists or is implied.

- **Letterboxed.** `height: 100vh` then `height: 100dvh` on the same rule, per the spec:
  the static unit is the fallback and the dynamic one takes over where supported, so the
  image does not jump as a mobile address bar shows and hides.
- **`<picture>` gets `display: contents`.** Without it the wrapper forms an inline box
  between the layout container and the `<img>`, which breaks percentage heights on the grid
  tile and centring on the detail page. Easy to miss because it only shows up once
  `<picture>` replaces a bare `<img>`.
- **Detail `sizes`** is `min(100vw, Nvh)`, where N is the photo's aspect ratio × 100 — a
  letterboxed image is bounded by height as often as by width, and plain `100vw` would have
  a portrait photo on a wide desktop download a variant several times larger than it
  displays. If a browser does not understand `min()` in `sizes` the attribute is ignored and
  it falls back to assuming 100vw, which is the old behaviour rather than a break.
- **Navigation** is hardcoded `<a href>`: Index top left, position counter top right, Prev
  and Next along the bottom, carrying `rel="prev"` / `rel="next"`. The sequence wraps, so
  there are no dead ends and every page has the same shape.
- **Prev/next are hand-maintained.** Inserting a photo into the middle of the sequence later
  means editing the two neighbouring pages as well as adding the new one. The sequence
  currently matches grid order, but nothing enforces that — they are independent by design.
- **Nav over photo.** From 700px up the image is inset so the controls never sit on it.
  Below that the photo is full-bleed and the labels sit over soft top and bottom gradient
  scrims — a monochrome collection will contain near-white and near-black frames alike, so
  the labels cannot rely on the image being dark. Over the empty letterbox surround the
  scrims are invisible, since they fade to exactly the surround colour.
- Hero image is `fetchpriority="high"` and not lazy — it is the LCP element on the page.

## 5. Swipe and keyboard navigation

`photo.js`, loaded `defer` on detail pages only. Both are shortcuts to links that already
exist in the markup, so with JavaScript off everything still works through the visible
controls.

- Swipe: `touchstart`/`touchend`, 50px horizontal threshold. Beyond the spec's sketch it
  also ignores gestures that are more vertical than horizontal (a scroll, not a swipe),
  slow drags over 800ms (a drag, not a flick), and anything involving a second finger.
- It also bails out when `visualViewport.scale > 1.05`. Pinch-to-zoom is native behaviour
  that needs no code — but once someone has zoomed in, a horizontal drag is them panning
  around the photo, and navigating out from under them would be hostile. Not fighting the
  zoom is the one thing this script owes it.
- Keyboard arrows are the desktop equivalent, listed in the spec's V2 notes and pulled
  forward because they share every line of the navigation logic with the swipe handler.
  Escape returns to the index. Modified keypresses are left alone — those belong to the
  browser.

## 6. Favicon, 404 and verification

- **Favicon** is an inline SVG data URI on every page. It fixes the 404 the browser was
  quietly logging on every request, and being a data URI it stays same-origin and costs no
  extra request.
- **404 page** (`404.html`), listed under the spec's V2 considerations and pulled forward
  because it is a dozen lines and reuses the existing tokens. Needs the host to be pointed
  at it; that is server configuration, not markup.
- **`prefers-reduced-motion`** also pulled forward from V2 — three lines, and switching the
  morph off for people who need it is not worth deferring.

Verified in a real Chromium build rather than by inspection:

- Grid renders 1 / 3 / 5 columns at 390px / 768px / 1440px.
- The grid-to-detail morph runs. Slowing the animation and capturing mid-flight frames
  confirms it behaves exactly as the spec predicts: the cropped thumbnail expands and the
  cropped-off parts of the frame come into view partway through — a resize-and-reveal, not a
  clean match-cut. It reads well; no change to the grid's cropping is warranted.
- Format and resolution negotiation works: a 227px-wide tile at DPR 1 fetches
  `demo-01-800.avif`, and a 712px detail image fetches the 800w AVIF rather than the 1600w.
- With JavaScript disabled, tile → detail → next → prev → index all still work, and images
  render. Nothing in the core experience depends on the script.
- `prefers-reduced-motion: reduce` resolves to `@view-transition { navigation: none }`.
- All three nav links hit-test to themselves at 44px tall at both 1280px and 390px, so
  nothing overlays the touch targets.
- All 11 pages load with no console errors, and every internal link resolves.

### Still open

- Open Graph tags. Deliberately skipped: unfurl images need absolute URLs, so this needs the
  production domain, and it belongs with the build script alongside per-page metadata.
- Alt-text policy for abstract images. The placeholders describe tonal structure
  ("pale grey light falling away to near-black") which is a reasonable model for photographs
  with no literal subject, but this should be a deliberate decision, not a default.
- Right-click / drag-save policy — still undecided, and nothing has been done either way.
- The 220px column floor should be re-checked once real photographs are in, on an actual
  phone rather than a resized desktop window.
