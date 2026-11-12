"""Research: dump outerHTML of the 'Производитель' filter group."""

from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, channel="msedge")
    page = browser.new_page()
    page.goto("https://catalog.onliner.by/tabletpc", timeout=90000, wait_until="domcontentloaded")
    page.wait_for_timeout(7000)
    html = page.evaluate(
        """() => {
          const groups = Array.from(document.querySelectorAll('.catalog-form__group'));
          const g = groups.find(el => (el.textContent || '').includes('Производитель'));
          return g ? g.outerHTML.slice(0, 3000) : null;
        }"""
    )
    print(html or "not found")
    browser.close()
