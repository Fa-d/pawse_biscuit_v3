"""Shared Lottie rasteriser: lottie-web (SVG renderer) inside headless Chromium via Playwright."""
import asyncio, io, json, os, sys
from PIL import Image
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
LOTTIE_JS = os.path.join(HERE, "..", "render", "node_modules", "lottie-web", "build", "player", "lottie.min.js")

HTML = """<!doctype html><html><head><meta charset=utf-8>
<style>html,body{margin:0;background:%(bg)s}#c{width:%(size)dpx;height:%(size)dpx;background:%(bg)s}</style>
</head><body><div id=c></div><script>%(js)s</script>
<script>
window.load = function(data){
  if (window.anim) { window.anim.destroy(); }
  document.getElementById('c').innerHTML='';
  window.anim = lottie.loadAnimation({container:document.getElementById('c'),renderer:'svg',loop:false,autoplay:false,animationData:data});
  return [window.anim.totalFrames, window.anim.frameRate];
};
window.seek = function(f){ window.anim.goToAndStop(f, true); };
</script></body></html>"""


async def _render(jobs, size, bg, scale):
    """jobs: list of (label, lottie_dict, frames) where frames is a list[int] or a callable(total)->list[int]."""
    with open(LOTTIE_JS) as f:
        js = f.read()
    html = HTML % {"bg": bg, "size": size, "js": js}
    out = []
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page(viewport={"width": size, "height": size}, device_scale_factor=scale)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        await pg.set_content(html)
        for label, data, frames in jobs:
            total, fr = await pg.evaluate("d => window.load(d)", data)
            total = int(round(total))
            fl = frames(total) if callable(frames) else [f for f in frames if f < total]
            imgs = []
            for fi in fl:
                await pg.evaluate("f => window.seek(f)", fi)
                png = await pg.locator("#c").screenshot()
                imgs.append((fi, Image.open(io.BytesIO(png)).convert("RGB")))
            out.append((label, total, imgs))
        await b.close()
    if errs:
        print("PAGE ERRORS:", errs[:10], file=sys.stderr)
    return out, errs


def render(jobs, size=256, bg="#f4efe9", scale=1.0):
    return asyncio.run(_render(jobs, size, bg, scale))


def even(n):
    def f(total):
        return [round(i * (total - 1) / (n - 1)) for i in range(n)] if n > 1 else [0]
    return f


def load(path):
    with open(path) as f:
        return json.load(f)
