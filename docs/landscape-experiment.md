# Putting a landscape photograph through the site

A one-off experiment, run and then reverted. The collection is nine portrait frames; this
was the first time anything wider than it was tall went through the pipeline. The photograph
itself is not in the repository — only what it taught us.

**Subject of the test:** a 4032x3024 phone photograph (4:3 landscape) of a marina at dusk,
against a collection of eight portrait frames between 0.66 and 0.71 wide-over-tall.

## The detail page handles it, and this is where the recent layout work pays

| viewport | rendered | under the previous CSS | difference |
|---|---|---|---|
| 1280x900 | **1131x848** | 1083x812 | +48 wide, +36 tall |
| 393x780 (phone upright) | 393x295 | — | 217px of surround above and below |
| 780x393 (phone turned) | 455x341 | — | — |

The desktop gain is the whole point of having removed the `>= 700px` insets. Those insets
existed to hold the photograph clear of a navigation overlay that no longer overlaps
anything, and on a portrait frame their removal was worth a modest 36px of height. On a
landscape frame it is 48px of width as well, because the 9rem horizontal inset was cutting
into the dimension a wide photograph actually uses. The layout needed no special case: the
bar reserves its row, the photograph takes what is left, and nothing overlaps at any size.

**A landscape photograph is simply small on a phone held upright**, and no layout can fix
that: a 1.33 frame in a 0.50 viewport letterboxes to 295px tall with 217px of empty surround
above and below. Turning the phone gets it to 455x341. This is worth knowing before
committing to landscape work in a collection people will mostly see on a phone.

## The grid is where a mixed collection actually bites

Tiles are a uniform 4:5 crop via `object-fit: cover`. On the marina that turns a wide sweep
into a tall centre slice — sky and masts, with the pontoon leading out of frame. Nothing is
broken; this is the trade-off section 3 of `notes.md` recorded deliberately ("a clean, even
grid at the cost of not showing each photo's real framing until the detail page"). With nine
portrait frames the cost was invisible. One landscape frame makes it the first thing you
notice.

Three ways out, none of them free:

- **Keep the uniform 4:5.** The grid stays calm and rhythmic. Landscape work reads as a crop
  and only resolves on the detail page. Defensible for one wide frame among nine; harder to
  defend as the proportion grows.
- **Let each tile take its own aspect ratio.** Honest framing everywhere, at the cost of a
  ragged grid — which some portfolios wear well.
- **Let landscape frames span two columns.** Reads as a deliberate layout rather than an
  accident, and the importer already computes the ratio it would need to emit a class for.
  The most work, and the best-looking answer if wide frames become a real part of the body
  of work.

The decision should follow the photography, not the other way round. It is not worth
rebuilding the grid for a single landscape frame, and it is worth doing properly the moment
there are several.

## Three practical findings

**Filename ordering is a trap for one-off additions.** Grid order is natural filename order,
so `IMG_0892.jpeg` sorted ahead of every `natural-light-…` file and silently became
photograph 1 of 9 — and therefore the eagerly-loaded LCP tile. Ordering by filename is a
good default because renaming is the whole interface, but it means a file dropped in with a
camera-assigned name lands wherever the alphabet puts it. See
`docs/importer-and-incremental-updates.md`; an explicit order is one of the proposals there.

**A landscape frame is the first to use the top of the resolution ladder.** The master cap
is set per aspect class, and portrait frames are capped below 3200px on the reasoning that
one letterboxed into a landscape viewport is never displayed that wide. A 4:3 frame lifts
that cap, so this was the first photograph to generate a 3200px variant: 84 files against 72
for eight portraits.

**Phone photographs carry GPS; the camera files did not.** Every Nikon original was free of
GPS, and the phone photograph had a full GPS IFD. The generated variants are clean — checked
across all three formats, zero EXIF tags, because the importer re-encodes through Pillow and
does not carry metadata across. The exposure risk is never the published site; it is the
original sitting in `photos-src/`, which the Pages workflow uploads with everything else.
Two policies fall out of that, and the repository should hold to both:

- Original files do not stay on a deployed branch.
- Anything phone-shot is assumed to carry location until checked.

## Verdict

The layout passed. The grid crop is the only real question a landscape photograph raises, and
it is a design decision rather than a defect. Revisit it when there is more than one wide
frame to show.
