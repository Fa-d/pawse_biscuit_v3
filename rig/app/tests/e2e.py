#!/usr/bin/env python3
"""End-to-end run of the studio in a real browser (your installed Chrome, through Playwright).

    STUDIO_DEV=1 .venv/bin/uvicorn app.main:app --port 8765 &
    .venv/bin/python -m app.tests.e2e http://localhost:8765 out/e2e

Walks the paths a person takes: the landing page's live examples, make a sticker from a prompt, edit it with chips, try to download while signed out,
create an account, download a free PNG, hit the paywall on an animated format, switch to Pro (dev helper), download a
Telegram file, save the sticker, open the collection, download a Telegram pack and send a report.  Saves a screenshot per step and fails on any page error.
"""
from __future__ import annotations

import os
import sys
import time

from playwright.sync_api import expect, sync_playwright


def main(base, out):
    os.makedirs(out, exist_ok=True)
    errors = []
    email = f"e2e-{int(time.time())}@example.com"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1366, "height": 900}, accept_downloads=True)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        def step(name):
            page.wait_for_selector("#stage:not(.busy)", timeout=30000)        # the newest preview is on screen
            page.screenshot(path=os.path.join(out, f"{name}.png"))

        page.goto(base + "/")
        expect(page.locator("#demo-sticker svg")).to_be_visible(timeout=30000)
        expect(page.locator("#cast li .cast-sticker svg")).to_have_count(3)
        page.wait_for_timeout(1500)
        page.screenshot(path=os.path.join(out, "00-landing.png"), full_page=True)
        page.click("text=Make your first sticker")
        expect(page).to_have_url(base + "/studio")
        expect(page.locator("#sticker svg")).to_be_visible(timeout=20000)
        step("01-first-load")

        page.fill("#prompt", "grumpy cat with sunglasses saying 'no.'")
        page.click("#make")
        expect(page.locator("#understood")).to_contain_text("grumpy")
        expect(page.locator('.group[data-slot="base"] button[aria-pressed="true"]')).to_have_text("Cat")
        expect(page.locator('.group[data-slot="face"] button[aria-pressed="true"]')).to_have_text("Angry")
        step("02-from-prompt")

        page.click('.group[data-slot="accessories"] button:has-text("Crown")')
        page.click('.group[data-slot="motion"] button:has-text("Dance")')
        expect(page.locator('.group[data-slot="motion"] button[aria-pressed="true"]')).to_have_text("Dance")
        page.wait_for_timeout(400)                        # past the editor's short pause before it asks for a preview
        step("03-edited")

        page.click('#download-row button:has-text("PNG")')
        expect(page.locator("#account-dialog")).to_be_visible()
        expect(page.locator("#account-title")).to_have_text("Create a free account")
        step("04-asked-to-sign-up")

        page.fill('#auth-form [name="email"]', email)
        page.fill('#auth-form [name="password"]', "correct horse battery")
        page.click("#auth-submit")
        expect(page.locator("#account-dialog")).to_be_hidden()
        expect(page.locator("#downloads-hint")).to_contain_text("free downloads left today")

        with page.expect_download() as dl:
            page.click('#download-row button:has-text("PNG")')
        path = dl.value.path()
        assert os.path.getsize(path) > 1000, "PNG download is empty"
        expect(page.locator("#downloads-hint")).to_contain_text("4 free downloads")
        step("05-free-png")

        page.click('#download-row button:has-text("Telegram")')
        expect(page.locator("#pricing-dialog")).to_be_visible()
        step("06-paywall")
        page.keyboard.press("Escape")

        page.click("#open-account")
        page.click('#dev-tools button:has-text("Make me Pro")')
        expect(page.locator("#open-account")).to_have_text("Pro")
        page.keyboard.press("Escape")
        page.wait_for_timeout(1500)                       # the preview loses its watermark
        with page.expect_download() as dl:
            page.click('#download-row button:has-text("Telegram")')
        assert dl.value.suggested_filename.endswith(".tgs"), dl.value.suggested_filename
        step("07-pro")

        page.click("#save")
        expect(page.locator("#toast")).to_contain_text("Saved")
        page.click("#open-collection")
        expect(page.locator("#sheet li")).to_have_count(1)
        page.wait_for_timeout(2500)
        step("08-collection")
        with page.expect_download(timeout=60000) as dl:
            page.click('#pack-actions button:has-text("Telegram pack")')
        assert dl.value.suggested_filename == "telegram-pack.zip", dl.value.suggested_filename
        page.click('#pack-actions button:has-text("WhatsApp pack, animated")')
        expect(page.locator("#toast")).to_contain_text("3 to 30")          # one saved sticker is too few for WhatsApp
        page.keyboard.press("Escape")

        page.click("#open-report")
        page.check('#report-form input[value="wrong"]')
        page.fill('#report-form [name="note"]', "I wanted it to wave")
        page.click('#report-form button[type="submit"]')
        expect(page.locator("#toast")).to_contain_text("Thanks")

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(500)
        wide = page.evaluate("document.documentElement.scrollWidth")
        step("09-phone")
        assert wide <= 390, f"page scrolls sideways on a phone ({wide}px wide)"
        browser.close()

    # 400/401/403 answers are refusals the steps above trigger on purpose and check on screen
    real = [e for e in errors if not any(f"status of {c}" in e for c in (400, 401, 403))]
    if real:
        print("page errors:", *real, sep="\n  ")
        return 1
    print("e2e passed; screenshots in", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765", sys.argv[2] if len(sys.argv) > 2 else "out/e2e"))
