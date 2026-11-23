# Example

A one-page site (an excerpt of 兰亭集序, public domain) set in [LXGW WenKai 霞鹜文楷](https://github.com/lxgw/LXGWWenKai) (SIL Open Font License).

1. Download `LXGWWenKaiGB-Regular.ttf` and `LXGWWenKaiGB-Medium.ttf` from [LXGW WenKai GB releases](https://github.com/lxgw/LXGWWenKaiGB/releases) into the repository root.
2. From the repository root:

```bash
python3 cjk_font_trim.py --site example/site --out example/site/fonts \
  --font "LXGW WenKai:400=LXGWWenKaiGB-Regular.ttf" \
  --font "LXGW WenKai:500=LXGWWenKaiGB-Medium.ttf"
```

The two source files are 52.3 MB; the output is 84 KB.

3. Serve the folder with any static server, e.g. `python3 -m http.server -d example/site`, and open http://localhost:8000/.
