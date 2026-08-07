# The importer, and how to add one photograph

Written after adding a ninth photograph turned out to be far harder than adding the first
eight. The importer is sound; the workflow around it has a hole, and this is a note on where
it is and how to close it.

## How it works today

`tools/import-photos.py` is a whole-collection build. It reads every image in `photos-src/`
and emits, in one pass:

- `img/<slug>-<width>.{avif,webp,jpg}` — the resolution ladder, trimmed per photograph
- `p/<slug>.html` — one detail page each
- the `<ul class="grid">` block inside `index.html`

`--prune` then deletes anything in `img/` and `p/` that the run did not produce. The folder
is the source of truth: whatever is in `photos-src/` **is** the collection, and everything
else is derived.

That is a good design for a first build and it is why the collection went from nine
gradients to eight photographs in a single command. It is the wrong design for adding one
photograph to a published site.

## The hole

Two policies are individually sensible and jointly broken.

1. The importer treats `photos-src/` as the complete collection.
2. Original files are deleted from the branch after a successful import, because the Pages
   workflow uploads the repository as-is and 39MB of full-resolution originals should not be
   published or carried in the deployed artifact.

Follow both and the source of truth is empty. Drop one photograph in and run the importer
and it does exactly what it is told: builds a one-photograph site and prunes the other eight
out of `img/`, `p/` and `index.html`.

This is not hypothetical. Adding a ninth photograph this session required
`git checkout e19a28a -- photos-src/` to pull 39MB of originals back out of history first,
purely so the importer could re-encode eight files that had not changed and did not need
re-encoding. A `--prune` run in a working tree where that restore had been forgotten would
have quietly deleted the live collection, and the diff would have been large enough that the
damage might not have been obvious before pushing.

**The immediate mitigation, until the below is built:** never run the importer without first
restoring the originals, and always read the dry-run summary — it prints the photograph count
before anything is written. `9 photographs` is right; `1 photograph` means stop.

## Why it rebuilds everything

Worth stating plainly, because it constrains the fix. Three things about a photograph's page
depend on the whole collection rather than on that photograph:

- the counter, `N of M` — every page changes when M changes
- `rel="prev"` / `rel="next"`, which wrap, so inserting a photograph rewires two neighbours
- grid order, which is document order in `index.html`

So *the HTML* genuinely is a whole-collection artifact and always will be. Adding one
photograph will always rewrite nine detail pages. That is fine — it is generated output, and
the churn is noise in a diff rather than risk.

What is **not** whole-collection is the expensive, original-requiring part: encoding twelve
image files per photograph. That only ever concerns the photograph being added.

That split is the whole answer.

## What to build

### 1. A committed manifest — the important one

Have the importer write `photos.json` alongside its output and read it on the next run: an
ordered list of entries carrying everything the HTML needs and the originals currently
supply.

```json
[
  { "slug": "natural-light-photo-museum-martin-mckenna-1",
    "source": "natural-light-photo-museum-martin-mckenna-1.jpg",
    "width": 2848, "height": 4288,
    "widths": [400, 800, 1600],
    "alt": "A person with closely cropped hair, …",
    "exif": { "camera": "Nikon D90", "lens": "18-200mm", "aperture": "f/5.6",
              "shutter": "1/100", "iso": 200, "taken": "2023-07-20T12:15:11" } }
]
```

With that in place the two halves separate cleanly:

- **HTML generation needs the manifest only.** Counters, prev/next, grid order, `srcset`
  lists, `width`/`height`, per-photo `sizes` — all derivable from the entries, with no
  original files present at all.
- **Image encoding needs an original**, and only for the entry being added or changed.

Adding a photograph becomes: drop one file in `photos-src/`, run the importer, commit,
delete the original. Nothing else needs to exist on disk. `--prune` becomes safe, because
the manifest defines the collection rather than the accident of which files happen to be in
a folder.

It also makes the EXIF captured at import time durable, which is a prerequisite for showing
any of it on the page — see the metadata discussion in `notes.md`. Today that data only
exists inside originals that are deliberately not kept.

### 2. Explicit modes rather than one implicit one

```
import-photos.py --add photos-src/new.jpg     # encode one, re-emit all HTML
import-photos.py --remove <slug>              # drop an entry, re-emit all HTML
import-photos.py --rebuild                    # today's behaviour; needs every original
```

`--rebuild` stays for changing an encoder setting or the ladder. It should refuse to run
when the manifest lists photographs whose originals are missing, rather than silently
building a smaller site — that single guard would have prevented the failure mode described
above.

### 3. An explicit order

Grid order is natural filename order, which makes renaming the whole interface for
sequencing — good, until a file arrives called `IMG_0892.jpeg` and lands at position 1
because `i` sorts before `n`. It also silently becomes the eagerly-loaded LCP tile. An
`order` field in the manifest, defaulting to append-at-end, lets a photograph be placed
without renaming it.

### 4. Stop uploading the repository as the site

The Pages workflow uses `path: .`, which is why originals cannot live in the repository
without also being published. Uploading only the site's own paths — `index.html`, `404.html`,
`styles.css`, `photo.js`, `img/`, `p/`, `.nojekyll` — decouples *in the repository* from
*on the site*.

That is worth doing on its own merits: it stops `notes.md`, `docs/` and `tools/` shipping to
visitors, and it shrinks the artifact. It also makes keeping originals in the repository a
real option rather than a hazard, if a growing collection ever makes the restore-from-history
step annoying enough to want gone. At roughly 2–5MB per 3200px export that stays reasonable
well past a hundred photographs.

## Recommendation

Build 1 and 2 together — they are the same change, and they turn adding a photograph from a
multi-step operation with a destructive failure mode into a one-liner. Add 3 when the order
first needs to be something other than alphabetical. Do 4 whenever the workflow is next
touched; it is small and independently worthwhile.

Until then, the rule is the one at the top: restore the originals first, and read the
dry-run count before writing.
