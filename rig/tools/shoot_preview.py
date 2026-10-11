#!/usr/bin/env python3
"""One look at the review page before publishing: desktop + phone, light + dark, inspector open.  Usage: shoot_preview.py page.html outdir"""
import asyncio, os, sys
from playwright.async_api import async_playwright

SKELETON = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>:root{color-scheme:light}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style></head><body>@@PAGE@@</body></html>"""


async def main(page_path, outdir):
    os.makedirs(outdir, exist_ok=True)
    html = SKELETON.replace("@@PAGE@@", open(page_path).read())
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        for name, w, h, scheme in (("desktop_light", 1280, 900, "light"), ("phone_light", 400, 800, "light"), ("desktop_dark", 1280, 900, "dark")):
            ctx = await b.new_context(viewport={"width": w, "height": h}, color_scheme=scheme)
            pg = await ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            await pg.route("**/*", lambda r: r.abort() if r.request.url.startswith("http") else r.continue_())
            await pg.set_content(html, wait_until="load")
            await pg.wait_for_timeout(900)
            overflow = await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            await pg.screenshot(path=os.path.join(outdir, f"{name}_top.png"))
            await pg.evaluate("document.getElementById('clips').scrollIntoView()")
            await pg.wait_for_timeout(700)
            await pg.screenshot(path=os.path.join(outdir, f"{name}_clips.png"))
            if name == "desktop_light":
                await pg.evaluate("document.getElementById('rig').scrollIntoView()")
                await pg.wait_for_timeout(700)
                await pg.screenshot(path=os.path.join(outdir, f"{name}_rig.png"))
                await pg.evaluate("document.getElementById('effects').scrollIntoView()")
                await pg.wait_for_timeout(700)
                await pg.screenshot(path=os.path.join(outdir, f"{name}_fx.png"))
            await pg.evaluate("document.getElementById('clips').scrollIntoView()")
            await pg.locator(".clip .btn").nth(1).click()
            await pg.wait_for_timeout(600)
            await pg.keyboard.press("ArrowRight")
            await pg.wait_for_timeout(200)
            await pg.screenshot(path=os.path.join(outdir, f"{name}_inspect.png"))
            cards = await pg.evaluate("document.querySelectorAll('.clip').length")
            svgs = await pg.evaluate("document.querySelectorAll('.lot svg').length")
            print(f"{name}: cards {cards}, live players {svgs}, horizontal overflow {overflow}px, errors {errs[:3]}")
            await ctx.close()
        await b.close()


asyncio.run(main(sys.argv[1], sys.argv[2]))
