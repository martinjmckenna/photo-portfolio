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

## 7. First GitHub Pages deployment failed

The `pages build and deployment` run on `921937c` failed. Breakdown of the three jobs:

- `build` — **succeeded** in 3 seconds. Jekyll processed the site and the artifact uploaded
  cleanly. Nothing in the repo broke the build.
- `report-build-status` — succeeded.
- `deploy` — **failed**. It polled `Current status: deployment_in_progress` every 5 seconds
  for ten minutes, then hit the action's own ceiling: `Timeout reached, aborting!`, followed
  by `Canceled deployment with ID 921937c…`.

So the artifact was fine and GitHub's Pages backend simply never finished publishing it.
There is no error from our content anywhere in the log — the failure is a stall on
GitHub's side, and the usual first move is to re-run it.

Ruled out:

- **DNS.** `www.martinmckenna.blog` is a CNAME to `martinjmckenna.github.io`, resolving to
  the four GitHub Pages addresses (185.199.108–111.153). The apex resolves there too.
  Correctly configured.
- **A stray `CNAME` file.** There is none, which is right: the site is a project page
  inheriting the domain from the user site, and committing a `CNAME` here would fight that.
- **Size.** ~7MB across ~110 files, nowhere near any Pages limit.
- **Our own workflow.** There isn't one. This is the built-in `dynamic/pages/…` workflow
  that comes from the "Publish from branch" setting.

Worth noting rather than concluding from: the deploy step evaluated the environment URL as
`http://www.martinmckenna.blog/photo-portfolio/` — plain HTTP, not HTTPS. That is what
GitHub reports when "Enforce HTTPS" is off, which normally means the TLS certificate for the
custom domain has not been provisioned yet. It is consistent with a Pages backend that is
still settling after the domain was configured, though it is not proof of the cause.

I could not confirm what the site currently serves: this sandbox's network policy denies
both `www.martinmckenna.blog` and `martinjmckenna.github.io`, so every probe came back as a
proxy 403 rather than an answer from the origin.

### One real bug found, unrelated to the failure

The environment URL confirms the site is published under a path prefix,
`/photo-portfolio/`, not at a domain root. Everything on the site uses relative URLs and is
fine with that — except `404.html`, which linked to `/index.html` and would therefore have
sent visitors to the root of the blog rather than back to the photo index. Now
`/photo-portfolio/`.

A relative link is not a fix here: GitHub Pages serves `404.html` at whatever path was
requested, so `index.html` would resolve against the depth of the missing URL rather than
the file's own location. That leaves this as the single URL on the site coupled to where it
is deployed, which is commented in place.

## 8. Pages deployment: second failure and the fix

Run 2 (`6ab706d`) reproduced run 1 exactly: `build` succeeded, `deploy` sat in
`deployment_in_progress` past the ten-minute mark. Two identical stalls in a row is not the
signature of a transient incident, so the earlier "just re-run it" read was wrong.

What the second run added:

- The uploaded artifact is **7,293,852 bytes**, matching the full local site. So Jekyll
  produced a complete build including all 93 image variants. Nothing is missing or
  malformed — the failure is entirely in the publish step, downstream of a valid artifact.
- The repo's own Pages settings are clean: source is the branch at `/ (root)`, and the
  custom domain field is **empty**.

### The domain, resolved

`www.martinmckenna.blog` is not configured on this repo. It is inherited: GitHub's settings
page describes custom domains as serving "from a domain other than `www.martinmckenna.blog`",
and it fills that blank with the *account's default Pages host*. That confirms the domain is
set on the user site repo (`martinjmckenna.github.io`), and a user-site custom domain
propagates to every project page on the account, each served at `<domain>/<repo>/`.

A consequence worth recording: `martinjmckenna.github.io` cannot be used as a prototyping
host while that is true. GitHub 301-redirects the whole `username.github.io` host to the
custom domain, project paths included. Serving this repo at `martinjmckenna.github.io/photo-portfolio/`
would require clearing the domain from the blog, which is not on the table.

So the site stays at `www.martinmckenna.blog/photo-portfolio/`. The blog is unaffected — the
user site repo keeps serving the domain root and every other path. The one thing to watch is
that a Jekyll page or post with the `photo-portfolio` slug would be shadowed by this project
page taking that prefix.

### Changes

- **`.nojekyll`.** The site is hand-authored HTML with nothing to template, so running it
  through Jekyll is pure downside: files beginning with `_` get dropped silently and
  anything resembling Liquid syntax gets interpreted. Nothing here trips either today, which
  is exactly why it is worth pinning before something does.
- **`.github/workflows/pages.yml`.** Replaces the built-in branch pipeline with
  `upload-pages-artifact` + `deploy-pages`: no Jekyll, and a deploy step whose logs we can
  read and whose runs we can re-trigger. This is deployment plumbing rather than a site build
  step — it generates and transforms nothing, so the spec's "no build tools" rule still holds.
  It needs Settings → Pages → Source switched to "GitHub Actions" to work.
- The trigger is `workflow_dispatch` only for now, deliberately: until the source is
  switched, a push-triggered run would just fail and add noise next to the legacy pipeline's
  own failures. The push trigger goes in after the first green run.

## 9. Pages deployment fixed

Switching the Pages source to "GitHub Actions" and deploying through
`upload-pages-artifact` + `deploy-pages` worked. Run `31115700017` on `528bfd4`:

```
Reported success!
Evaluated environment url: http://www.martinmckenna.blog/photo-portfolio/
```

The deploy step took 3m10s. Worth noting what it did *not* do differently: it polled
`Current status: deployment_in_progress` exactly like the legacy pipeline, and simply
finished instead of being killed at the ten-minute ceiling. Same site, same artifact
contents, different publish path.

So the root cause in GitHub's legacy `dynamic/pages/pages-build-deployment` pipeline is
still unknown — this routes around it rather than explaining it. If it matters later, the
evidence is runs `31112057191` and `31114481029`, both dying at exactly 10.1 minutes after
uploading a valid 7,293,852-byte artifact.

Follow-ups applied:

- Push trigger added to the workflow now that the source switch is confirmed working, so
  commits to this branch deploy on their own.
- The run logs a warning that `actions/checkout@v4`, `configure-pages@v5`,
  `deploy-pages@v4` and `upload-artifact@v4` target Node 20 and are being forced onto Node
  24. These are the current major versions of each action, so there is nothing to bump —
  it resolves when the actions themselves ship Node 24 builds.

### Not verified from here

The sandbox's network policy denies `www.martinmckenna.blog` and `martinjmckenna.github.io`,
so every request came back a proxy 403. GitHub reports the deployment as successful, but
nobody has yet loaded the site itself. Still worth an eye on, in a browser:

- Whether the grid, a detail page and the morph behave as they did locally.
- Whether `https://` works. GitHub evaluated the URL as `http://` because "Enforce HTTPS" is
  unchecked on this repo; the certificate belongs to the domain and the blog already serves
  it, so HTTPS will probably just work, but that checkbox is where to look if it does not.
- Whether the blog has a page or post on the `photo-portfolio` slug, which this project page
  would now shadow.

### Verified live

Loaded on an actual phone: the grid renders, the tiles hold their 4:5 crop, dark mode is
picked up from the OS, and the site is served from `martinmckenna.blog`. The deployment is
genuinely working, not just reported as working.

That closes the last item the spec left hanging on the grid: the 220px column floor, judged
on a real device rather than a resized desktop window. One column at phone width, which
reads well — each photograph gets the full width and the crop has room to breathe. The
trade-off is that a longer collection means a lot of scrolling; if that starts to feel slow
once there are more than a dozen photographs, dropping the floor to around 160px would give
two columns at phone width. Leaving it at 220px for now: with real photographs the larger
single column is the better first impression.

## 9. Import pipeline for the real photographs

`tools/import-photos.py` replaces the hand-editing loop the README used to describe.
Sources go in `photos-src/`, and one run writes `img/`, writes `p/<slug>.html`, and rewrites
the `<ul class="grid">` block in `index.html`. Everything the old instructions asked for by
hand — the three `srcset` lists per photo, the `width`/`height` attributes, the per-photo
`sizes`, the matching `view-transition-name`s and the wrapping prev/next chain — is now
derived from the source files.

This is the build script the notes kept deferring to, and it stays on the same side of the
"no build tools" line as `make-placeholders.py`: it runs at development time, its output is
committed as plain HTML, and nothing is installed or executed to serve the site.

- **Ordering is filename order**, sorted naturally so `2-` precedes `10-`. Making the
  filenames the ordering mechanism means sequencing the collection is renaming files, with
  no manifest to keep in sync. `--order exif` sequences by capture time instead.
- **Slugs come from filenames**, so URLs are readable and stable rather than `demo-NN`.
- **sRGB conversion and EXIF rotation** happen on the way in. Both are silent-failure cases
  otherwise: an Adobe RGB export renders desaturated in a browser if its profile is dropped
  without converting, and an orientation flag is honoured by some encoders and ignored by
  others. Normalising once at import means the variants are all right way up and right
  colour regardless of what the source was.
- **The master cap by aspect class** is carried over from `make-placeholders.py` rather
  than reinvented — same reasoning, now applied to real sources, and a source smaller than
  a ladder rung is never upscaled to fill it.
- **Alt text cannot be generated**, so it is the one input the script asks for, in
  `photos-src/captions.txt`. A photo without a caption is still imported — a missing
  description should not block a build — but it gets obviously-placeholder alt text and is
  listed at the end of the run. That also settles the open question from section 6: the
  alt-text policy is a human sentence per photograph, authored alongside the photo.
- **Deleting is opt-in.** `--prune` removes what the run did not produce; without it stale
  files are only listed. The default run writes nothing at all, so the first thing you see
  is a summary rather than a changed working tree.

Verified end to end before any real photographs existed, against synthetic sources chosen
for the awkward cases: a 4000px landscape, a source smaller than the bottom rung, a PNG, an
EXIF-rotated portrait, mixed `2-`/`10-` numbering, and a 9:16 crop. All 157 asset references
across the generated pages resolve, no file in `img/` is orphaned, the prev/next chain forms
one complete cycle, and Chromium loads the grid and a detail page with no console or network
errors, picking the AVIF variants.

### Still open

- `index.html` still describes the collection as "monochrome photographs", and the site's
  own chrome is monochrome by design. If the real photographs are in colour, that meta
  description is the line to change — the stylesheet does not need to.
- `photos-src/` ships with the Pages artifact, which uploads the repository as-is. The
  originals should come off the branch once an import looks right.
