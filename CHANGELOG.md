# Changelog

## 0.1.0 (2026-11-23)

First public release.

- Scan built pages in a real browser at desktop (1440×900) and phone (390×844) width
- Per family and weight subsets in woff2, plus a separate first-screen file per family/weight
- `fonts.css` with `unicode-range` so the first-screen file wins for its characters
- `--top-pages` to choose which pages' first screen goes into the small files (default `/`)
- `--top-exclude` to keep animated or long first-screen elements out of the small files
