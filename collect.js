// Render each page in a real browser (desktop and phone widths) and record, per font family and weight,
// every character actually displayed ("all") and the characters visible on the first screen ("top").
// Called by cjk_font_trim.py; prints JSON to stdout.
//
// usage: node collect.js <config.json>
//   { "site": "dist", "pages": ["/", "/about/"], "families": ["Noto Sans SC", "Noto Serif SC"],
//     "topExclude": "figure,.demo", "chrome": false }
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const ORIGIN = 'https://site.local';  // https, so pages with upgrade-insecure-requests in their CSP still load
const TYPES = {
  '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.gif': 'image/gif', '.avif': 'image/avif', '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.otf': 'font/otf',
};

(async () => {
  const browser = await chromium.launch(cfg.chrome ? { channel: 'chrome' } : {});
  const out = { all: {}, top: {} };
  for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    const ctx = await browser.newContext({ viewport });
    // Serve pages straight from the build folder; block everything external (web fonts, analytics, ...).
    await ctx.route('**/*', route => {
      const u = new URL(route.request().url());
      if (u.origin !== ORIGIN) return route.abort();
      let f = path.join(cfg.site, decodeURIComponent(u.pathname));
      if (f.endsWith(path.sep) || f.endsWith('/')) f = path.join(f, 'index.html');
      if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) return route.fulfill({ status: 404, body: '' });
      route.fulfill({ status: 200, body: fs.readFileSync(f), contentType: TYPES[path.extname(f).toLowerCase()] || 'application/octet-stream' });
    });
    for (const p of cfg.pages) {
      const page = await ctx.newPage();
      await page.goto(ORIGIN + p, { waitUntil: 'load' });
      await page.waitForTimeout(300);
      const r = await page.evaluate(({ families, topExclude }) => {
        const all = {}, top = {};
        const norm = s => s.trim().replace(/^["']|["']$/g, '').toLowerCase();
        const wanted = families.map(norm);
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        const range = document.createRange();
        while (walker.nextNode()) {
          const n = walker.currentNode, el = n.parentElement;
          if (!el || el.closest('script,style,noscript,template')) continue;
          const s = getComputedStyle(el);
          // first family in the computed font stack that we were asked to trim
          const fam = s.fontFamily.split(',').map(norm).find(f => wanted.includes(f));
          if (!fam) continue;
          const key = families[wanted.indexOf(fam)] + '|' + s.fontWeight;
          all[key] = (all[key] || '') + n.data;
          if (topExclude && el.closest(topExclude)) continue;
          range.selectNodeContents(n);
          const b = range.getBoundingClientRect();
          if (b.height > 0 && b.top < innerHeight && b.bottom > 0) top[key] = (top[key] || '') + n.data;
        }
        return { all, top };
      }, { families: cfg.families, topExclude: cfg.topExclude || '' });
      for (const part of ['all', 'top']) for (const [k, v] of Object.entries(r[part])) out[part][k] = (out[part][k] || '') + v;
      await page.close();
    }
    await ctx.close();
  }
  await browser.close();
  for (const part of Object.values(out)) for (const k of Object.keys(part)) part[k] = [...new Set(part[k])].join('');
  process.stdout.write(JSON.stringify(out));
})().catch(e => { console.error(e.message); process.exit(1); });
