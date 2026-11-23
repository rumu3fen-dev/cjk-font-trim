# cjk-font-trim

Subset Chinese / Japanese / Korean web fonts to **the characters your static site actually shows**, and split out a tiny **first-screen** file so headings render in the right font almost immediately.

A full CJK font is 16–25 MB per weight. A typical page shows a few hundred distinct characters. This tool opens every page of your built site in a real browser, records which characters are displayed in which font and weight, and writes trimmed `.woff2` files plus the `@font-face` CSS.

```
4 source fonts (Noto Sans/Serif SC, 4 weights)   82.0 MB
after cjk-font-trim, 3 pages                      0.75 MB
  of which first-screen files                     0.12 MB
```

## Why not just subset by text?

Static subsetting tools usually read the HTML source. That misses text inserted by scripts, counts text that is never shown (hidden menus, `aria-hidden` decorations), and can't tell which weight a character is rendered in. Rendering the page in a browser answers all three: `getComputedStyle()` gives the real family and weight for every text node.

It also checks what is visible **in the first viewport** (desktop 1440×900 and phone 390×844). Those characters go into a separate small file, declared last with `unicode-range`, so the browser fetches ~20–80 KB before it can paint the hero in the right font, and loads the rest afterwards.

## Install

```
pip install -r requirements.txt     # fonttools + brotli
npm install                         # playwright
npx playwright install chromium     # or pass --chrome to use your installed Google Chrome
```

## Use

Build your site first, then:

```
python3 cjk_font_trim.py --site dist --out dist/fonts --url /fonts/ \
  --font "Noto Sans SC:400=fonts/NotoSansCJKsc-Regular.otf" \
  --font "Noto Sans SC:500=fonts/NotoSansCJKsc-Medium.otf" \
  --font "Noto Serif SC:300=fonts/NotoSerifCJKsc-Light.otf"
```

- `--font "FAMILY:WEIGHT=FILE"`: one per family and weight. `FAMILY` is the name your CSS uses in `font-family`; it can appear anywhere in the font stack (`"Source Serif 4","Noto Serif SC",serif` works).
- `--pages / /about/`: limit the scan; default is every `.html` file in `--site`.
- `--top-exclude "figure,.demo"`: first-screen text that can wait for the full font (animations, screenshots, long paragraphs). Keeps the first-screen file small.
- Computed weights are folded into the nearest weight you supplied (a `450` lands on `400` or `500`).

Output in `--out`:

| file | contains |
|---|---|
| `<family>-<weight>.woff2` | every character the pages show in that family/weight, plus ASCII and common CJK punctuation |
| `<family>-<weight>-top.woff2` | only the first-screen characters |
| `fonts.css` | `@font-face` rules: full files first, first-screen files last with `unicode-range` |

Replace your existing `@font-face` rules with `fonts.css`, and preload the first-screen files:

```html
<link rel="preload" href="/fonts/noto-serif-sc-300-top.woff2" as="font" type="font/woff2" crossorigin>
```

Run it again whenever the text changes (it's fast enough to put in the build).

## Multilingual sites

Run once per language with that language's pages and output folder. Pan-CJK fonts such as Noto CJK switch glyph shapes by `<html lang>` through the OpenType `locl` feature; the tool keeps all layout features, so the same source font serves Simplified Chinese, Traditional Chinese and Japanese pages correctly.

## Notes

- Requires Python 3.9+, Node 18+.
- Pages are served straight from the build folder; all external requests (web fonts, analytics) are blocked during the scan.
- Characters that only appear after user interaction (opening a menu, a later step of a form) are counted if they are in the DOM when the page has loaded. Text fetched later at runtime is not; add those pages or states yourself, or rely on the font stack's fallback.

## 中文说明

把中日韩网页字体裁成「网站真正显示的字」，并把打开页面第一屏看得见的字单独拆成一个很小的文件，先下载、先显示。完整的中文字体每个字重 16–25 MB，裁完通常只剩几十到几百 KB。用浏览器真实渲染每个页面来统计，脚本插入的字、真正用到的字重都算得准。用法见上文。

## License

MIT. Built by [入木 INGRAIN](https://rumu3fen.com/en/) for [rumu3fen.com](https://rumu3fen.com/), which uses it to serve four languages from one set of Noto CJK fonts.
