# Source photographs

Drop the original photographs in this folder, then run:

```sh
python3 tools/import-photos.py            # dry run: shows what it would do
python3 tools/import-photos.py --write --prune
```

That writes `img/` and `p/` and rewrites the grid in `index.html`. Everything it
touches is generated — don't hand-edit those files, the next run overwrites them.

## Naming sets the order

Grid order is filename order, sorted naturally (`2-` before `10-`). Prefix the files
to arrange the collection:

```
01-harbour-wall.jpg
02-stairwell.jpg
03-window.jpg
```

The filename also becomes the URL slug — `01-harbour-wall.jpg` becomes
`p/01-harbour-wall.html` — so it is worth naming them readably. Pass `--order exif`
to sequence by capture time instead of filename.

## Captions

`captions.txt` holds the alt text, one photo per line, keyed by filename:

```
01-harbour-wall.jpg | Wet harbour wall at low tide, ropes coiled against the stone.
```

A photo with no caption still gets imported, but its alt text is a stand-in derived
from the filename and the script lists it at the end of the run. Alt text is the only
part of this that cannot be generated — it is what the site reads like to anyone using
a screen reader, and it becomes each detail page's `<meta name="description">` too.

## Formats and size

JPEG, PNG, TIFF, WebP, AVIF and HEIC are all accepted. Colour profiles are converted
to sRGB and EXIF rotation is applied, so exports from Lightroom or Photos come in the
right way up and the right colour.

The top of the resolution ladder is 3200px wide, so anything larger than that is only
downscaled — exporting at 3200px on the long edge keeps the repository small and costs
the site nothing.

## These originals do not belong on the deployed site

The Pages workflow uploads the repository as-is, so this folder ships with it. Once the
import has run and the output looks right, delete the originals from the branch — `img/`
holds everything the site actually serves.
