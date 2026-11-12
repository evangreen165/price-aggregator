"""Research: final DOM probe of Deal.by/21vek/shop.by after JS render."""

from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TARGETS = {
    "dealby": "https://deal.by/search/?q=телевизор",
    "21vek": "https://www.21vek.by/search/?text=телевизор",
    "shopby": "https://shop.by/search/?q=телевизор",
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="msedge")
    for name, url in TARGETS.items():
        page = browser.new_page()
        page.goto(url, timeout=90000, wait_until="domcontentloaded")
        page.wait_for_timeout(10000)
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(4000)
        body = page.evaluate("() => document.body.innerText.slice(0, 250)")
        links = page.eval_on_selector_all(
            "a[href]",
            """els => els.map(a => [a.getAttribute('href') || '', (a.getAttribute('title') || a.textContent || '').trim().slice(0, 60)])
                 .filter(([h, t]) => t && (h.includes('/item/') || h.includes('/products/') || h.includes('/p/')))""",
        )
        print(f"{name}: body={body.replace(chr(10), ' | ')[:180]}")
        print(f"{name}: product-like links={len(links)}")
        for link in links[:4]:
            print("   ", link)
        page.close()
    browser.close()
