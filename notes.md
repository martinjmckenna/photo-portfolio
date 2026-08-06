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
