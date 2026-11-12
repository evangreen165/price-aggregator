"""Research: Deal.by DOM product cards after scroll (lazy-load)."""

from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="msedge")
        page = browser.new_page()
        page.goto("https://deal.by/search/?q=телевизор", timeout=90000, wait_until="domcontentloaded")
        for _ in range(8):
            page.wait_for_timeout(2500)
            page.mouse.wheel(0, 3000)
        for selector in (".product-card", ".product-item", "[class*='product']", "a[href*='/item/']", "a[href*='/goods/']"):
            print(selector, "->", page.locator(selector).count())
        links = page.locator("a[href*='/item/'], a[href*='/goods/']")
        print("sample links:", links.count())
        if links.count():
            print("  first:", links.first.get_attribute("href"), "|", (links.first.get_attribute("title") or "")[:50])
        browser.close()


if __name__ == "__main__":
    main()
