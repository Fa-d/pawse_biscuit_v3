#!/usr/bin/env python3
"""QA for built Lottie files.

For every file: load in lottie-web (collect player errors), render EVERY frame small, then report
  * frame-to-frame change spikes (possible pops / glitches)
  * loop seam: change between the last frame and frame 0, compared with normal frame-to-frame change
  * how close the artwork gets to each canvas edge (clipping)
  * metadata vs. the original file of the same name (size, fps, frame count)

Usage: check.py [--orig raw] [--size 128] [--report out/qa.json] file.json ...
"""
import argparse, asyncio, io, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
from playwright.async_api import async_playwright
import lr

BG = (255, 0, 255)   # magenta: never used by the artwork


async def run(files, size, orig_dir):
    with open(lr.LOTTIE_JS) as f:
        js = f.read()
    html = lr.HTML % {"bg": "#ff00ff", "size": size, "js": js}
    report = []
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page(viewport={"width": size, "height": size})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type in ("error", "warning") else None)
        await pg.set_content(html)
        for fp in files:
            errs.clear()
            data = lr.load(fp)
            total, fr = await pg.evaluate("d => window.load(d)", data)
            total = int(round(total))
            frames = []
            for f in range(total):
                await pg.evaluate("f => window.seek(f)", f)
                png = await pg.locator("#c").screenshot()
                frames.append(np.asarray(Image.open(io.BytesIO(png)).convert("RGB"), dtype=np.int16))
            A = np.stack(frames)
            d = np.abs(A[1:] - A[:-1]).mean(axis=(1, 2, 3))            # change per frame step
            seam = float(np.abs(A[0] - A[-1]).mean())
            med = float(np.median(d)) if len(d) else 0.0
            p90 = float(np.percentile(d, 90)) if len(d) else 0.0
            spikes = [(int(i + 1), round(float(v), 2)) for i, v in enumerate(d) if v > max(4 * p90, 1.2)]
            art = np.any(np.abs(A - np.array(BG, dtype=np.int16)) > 40, axis=3)     # (frames, h, w) artwork mask
            k = 512.0 / size
            margins = {}
            for name, strip in (("top", art[:, :2, :]), ("bottom", art[:, -2:, :]), ("left", art[:, :, :2]), ("right", art[:, :, -2:])):
                hit = np.where(strip.reshape(total, -1).any(axis=1))[0]
                margins[name] = [int(hit[0]), int(hit[-1]), int(len(hit))] if len(hit) else None
            ys, xs = np.where(art.any(axis=0))
            bbox = [round(float(xs.min() * k)), round(float(ys.min() * k)), round(float((xs.max() + 1) * k)), round(float((ys.max() + 1) * k))] if len(xs) else None
            meta = dict(w=data["w"], h=data["h"], fr=data["fr"], op=data["op"], layers=len(data["layers"]), bytes=os.path.getsize(fp))
            same = None
            if orig_dir:
                op_ = os.path.join(orig_dir, os.path.basename(fp))
                if os.path.exists(op_):
                    o = lr.load(op_)
                    same = all(o[k_] == data[k_] for k_ in ("w", "h", "fr", "op", "ip"))
            report.append(dict(file=os.path.basename(fp), meta=meta, errors=list(errs), median_change=round(med, 3), p90_change=round(p90, 3),
                               seam_change=round(seam, 3), spikes=spikes, edges=margins, bbox=bbox, matches_original=same))
        await b.close()
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--orig", default=None)
    ap.add_argument("--size", type=int, default=128)
    ap.add_argument("--report", default=None)
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    rep = asyncio.run(run(a.files, a.size, a.orig))
    if a.report:
        json.dump(rep, open(a.report, "w"), indent=1)
    for r in rep:
        m = r["meta"]
        flag = "" if not r["errors"] else "  PLAYER ERRORS: " + "; ".join(r["errors"][:2])
        print(f"{r['file']:<32} {m['w']}x{m['h']} {m['fr']}fps {m['op']:>3}f {m['layers']:>2}L {m['bytes'] / 1024:>6.1f}KB"
              f"  orig-meta={'ok' if r['matches_original'] else ('-' if r['matches_original'] is None else 'DIFF')}"
              f"  change med {r['median_change']:.2f} p90 {r['p90_change']:.2f}  seam {r['seam_change']:.2f}{flag}")
        if r["spikes"]:
            print("      spikes (frame, change):", r["spikes"][:12])
        ed = {k: v for k, v in r["edges"].items() if v}
        print("      bbox", r["bbox"], " touches edges:", ed if ed else "none")
