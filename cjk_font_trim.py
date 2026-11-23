#!/usr/bin/env python3
"""cjk-font-trim: subset CJK web fonts to the characters your static site actually shows,
and split out a tiny "first screen" file so text renders in the right font almost immediately.

    python3 cjk_font_trim.py --site dist --out dist/fonts --url /fonts/ \
        --font "Noto Sans SC:400=NotoSansCJKsc-Regular.otf" \
        --font "Noto Sans SC:700=NotoSansCJKsc-Bold.otf" \
        --font "Noto Serif SC:300=NotoSerifCJKsc-Light.otf"

Writes, for every family/weight: <slug>-<weight>-top.woff2 (first-screen characters), <slug>-<weight>.woff2 (everything else),
and fonts.css with the @font-face rules. Link fonts.css (or paste it) instead of your current @font-face rules.
"""
import argparse, json, os, pathlib, re, subprocess, sys, tempfile

from fontTools import subset

HERE = pathlib.Path(__file__).resolve().parent
# ASCII and common CJK punctuation always go into the "rest" file, so text added later by scripts still has them
BASE = {chr(c) for c in range(0x20, 0x7f)} | set('，。、：；！？（）《》「」『』“”‘’—…·／～％＋・')


def parse_font(spec):
    m = re.fullmatch(r'(.+?):(\d{3})=(.+)', spec)
    if not m:
        raise SystemExit(f'--font must look like "Family Name:400=path/to/font.otf", got {spec!r}')
    family, weight, file = m.group(1).strip(), int(m.group(2)), pathlib.Path(m.group(3)).expanduser()
    if not file.exists():
        raise SystemExit(f'font file not found: {file}')
    return family, weight, file


def find_pages(site):
    pages = []
    for f in sorted(site.rglob('*.html')):
        rel = '/' + f.relative_to(site).as_posix()
        pages.append(rel[:-len('index.html')] if rel.endswith('/index.html') else rel)
    return pages


def unicode_range(chars):
    cps = sorted({ord(c) for c in chars})
    out, i = [], 0
    while i < len(cps):
        j = i
        while j + 1 < len(cps) and cps[j + 1] == cps[j] + 1:
            j += 1
        out.append(f'U+{cps[i]:X}' + (f'-{cps[j]:X}' if j > i else ''))
        i = j + 1
    return ','.join(out)


def make_subset(src, chars, dst):
    opts = subset.Options()
    opts.flavor = 'woff2'
    opts.layout_features = ['*']  # keep locl, vert, kern, ...: Pan-CJK fonts switch glyphs by language through locl
    opts.name_IDs = ['*']
    font = subset.load_font(str(src), opts)
    sub = subset.Subsetter(opts)
    sub.populate(text=''.join(sorted(chars)))
    sub.subset(font)
    subset.save_font(font, str(dst), opts)
    return dst.stat().st_size


def nearest(weight, available):
    return min(available, key=lambda w: (abs(w - weight), w))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--site', required=True, type=pathlib.Path, help='built static site folder')
    ap.add_argument('--font', required=True, action='append', metavar='"FAMILY:WEIGHT=FILE"',
                    help='source font for one family/weight; repeat for each (family = the name used in your CSS)')
    ap.add_argument('--out', required=True, type=pathlib.Path, help='where to write the .woff2 files and fonts.css')
    ap.add_argument('--url', default='/fonts/', help='URL prefix the browser loads the fonts from (default /fonts/)')
    ap.add_argument('--pages', nargs='*', help='page paths to scan, like / /about/ (default: every .html file in --site)')
    ap.add_argument('--top-pages', nargs='*', metavar='PATH',
                    help='pages whose first screen goes into the small *-top files (default: / if scanned, else the first page). '
                         'Every other page still counts toward the full files.')
    ap.add_argument('--top-exclude', default='', metavar='SELECTOR',
                    help='CSS selector for first-screen text that may wait for the full font (e.g. animated demos)')
    ap.add_argument('--chrome', action='store_true', help='use the installed Google Chrome instead of Playwright Chromium')
    a = ap.parse_args()

    fonts = {}
    for spec in a.font:
        family, weight, file = parse_font(spec)
        fonts.setdefault(family, {})[weight] = file
    pages = a.pages or find_pages(a.site)
    top_pages = a.top_pages if a.top_pages is not None else (['/'] if '/' in pages else pages[:1])
    print(f'scanning {len(pages)} page(s) for {", ".join(fonts)}; first screen from {" ".join(top_pages) or "(none)"} …', file=sys.stderr)

    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as cfg:
        json.dump({'site': str(a.site.resolve()), 'pages': pages, 'families': list(fonts),
                   'topPages': top_pages, 'topExclude': a.top_exclude, 'chrome': a.chrome}, cfg)
    try:
        res = subprocess.run(['node', str(HERE / 'collect.js'), cfg.name], check=True, capture_output=True, text=True, cwd=HERE)
    except subprocess.CalledProcessError as e:
        raise SystemExit(f'browser scan failed:\n{e.stderr}')
    finally:
        os.unlink(cfg.name)
    seen = json.loads(res.stdout)

    # The browser reports computed weights (e.g. 450); fold each into the nearest weight we have a file for.
    need, top = {}, {}
    for part, target in (('all', need), ('top', top)):
        for key, chars in seen[part].items():
            family, weight = key.rsplit('|', 1)
            w = nearest(int(weight), fonts[family])
            target.setdefault((family, w), set()).update(chars)

    a.out.mkdir(parents=True, exist_ok=True)
    rest_faces, top_faces, total = [], [], 0
    for family, weights in fonts.items():
        slug = re.sub(r'[^a-z0-9]+', '-', family.lower()).strip('-')
        for w, src in sorted(weights.items()):
            all_chars = need.get((family, w), set())
            first = top.get((family, w), set()) - {' ', '\n', '\t'}
            if not all_chars:
                print(f'  {family} {w}: not used on any page, skipped', file=sys.stderr)
                continue
            name = f'{slug}-{w}'
            rest_size = make_subset(src, (all_chars - first) | BASE, a.out / f'{name}.woff2')
            rest_faces.append(f'@font-face{{font-family:"{family}";font-weight:{w};font-style:normal;font-display:swap;'
                              f'src:url({a.url}{name}.woff2) format("woff2")}}')
            line = f'  {family} {w}: {len(all_chars)} chars → {name}.woff2 {rest_size / 1024:.0f} KB'
            total += rest_size
            if first:
                top_size = make_subset(src, first, a.out / f'{name}-top.woff2')
                top_faces.append(f'@font-face{{font-family:"{family}";font-weight:{w};font-style:normal;font-display:swap;'
                                 f'src:url({a.url}{name}-top.woff2) format("woff2");unicode-range:{unicode_range(first)}}}')
                line += f'\n{" " * (len(family) + len(str(w)) + 4)}+ {name}-top.woff2 {top_size / 1024:.0f} KB ({len(first)} first-screen chars)'
                total += top_size
            print(line, file=sys.stderr)

    # Same family declared twice: browsers match @font-face rules in reverse order, so the small first-screen file
    # (declared last, limited by unicode-range) wins for its characters and the rest file covers everything else.
    css = '/* generated by cjk-font-trim */\n' + '\n'.join(rest_faces + top_faces) + '\n'
    (a.out / 'fonts.css').write_text(css, encoding='utf-8')
    source = sum(f.stat().st_size for f in {f for ws in fonts.values() for f in ws.values()})
    print(f'done: {total / 1024:.0f} KB of fonts (source: {source / 1e6:.1f} MB), rules in {a.out / "fonts.css"}', file=sys.stderr)
    print('tip: <link rel="preload" as="font" type="font/woff2" crossorigin> the *-top.woff2 files you use above the fold.',
          file=sys.stderr)


if __name__ == '__main__':
    main()
