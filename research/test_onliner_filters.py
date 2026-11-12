"""Research: Onliner filters via Playwright headless (category page DOM).

Run: python research/test_onliner_filters.py
"""

from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_FILTER_JS = """els => els.map(g => {
  const caption = g.querySelector('.catalog-form__label-title');
  const options = Array.from(g.querySelectorAll('ul.catalog-form__checkbox-list span'))
      .map(s => (s.textContent || '').trim()).filter(Boolean);
  return { title: caption ? caption.textContent.trim() : null, options: options };
}).filter(g => g.title && g.options.length)"""


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="msedge")
        page = browser.new_page()
        page.goto("https://catalog.onliner.by/tabletpc", timeout=90000, wait_until="domcontentloaded")
        page.wait_for_timeout(7000)
        groups = page.eval_on_selector_all(".catalog-form__group", _FILTER_JS)
        print(f"onliner filter groups: {len(groups)}")
        for group in groups[:8]:
            print("  -", group["title"], "| options:", group["options"][:6])
        browser.close()


if __name__ == "__main__":
    main()
