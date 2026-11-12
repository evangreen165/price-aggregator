"""Research: aliexpress.ru search — patience probe with scrolling."""

from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SELECTOR = "a[href*='/item/']"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="msedge")
    page = browser.new_page()
    Stealth().use_sync(page)
    page.goto("https://aliexpress.ru/search?text=телевизор", timeout=90000, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    for _ in range(6):
        page.mouse.wheel(0, 2500)
        page.wait_for_timeout(2500)
    total = page.locator(SELECTOR).count()
    print("aliexpress.ru item links after scrolls:", total)
    if total:
        print("  first href:", page.locator(SELECTOR).first.get_attribute("href"))
        print("  first title:", (page.locator(SELECTOR).first.get_attribute("title") or "")[:70])
    browser.close()
