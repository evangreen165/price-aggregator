"""Research: Wildberries via Playwright + stealth (msedge, headful).

Intercepts search.wb.ru XHR and falls back to __NEXT_DATA__ / DOM.
"""

from __future__ import annotations

import json

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

QUERY = "телевизор"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="msedge")
        context = browser.new_context(locale="ru-RU", viewport={"width": 1400, "height": 900})
        page = context.new_page()
        Stealth().use_sync(page)

        search_responses: list[dict] = []

        def on_response(response) -> None:
            if "search.wb.ru" in response.url:
                try:
                    search_responses.append(response.json())
                except Exception:
                    pass

        page.on("response", on_response)

        print("[wb] opening search page...")
        page.goto(
            f"https://www.wildberries.ru/catalog/0/search.aspx?search={QUERY}",
            timeout=90000,
            wait_until="domcontentloaded",
        )
        page.wait_for_timeout(8000)
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        print("[wb] page title:", page.title()[:80])

        body_text = page.evaluate("() => document.body.innerText.slice(0, 300)")
        print("[wb] body snippet:", body_text.replace("\n", " | ")[:250])

        next_data = page.evaluate(
            "() => { const n = document.querySelector('script#__NEXT_DATA__'); return n ? n.textContent.slice(0, 200) : null; }"
        )
        print("[wb] __NEXT_DATA__ present:", next_data is not None, next_data)

        print(f"[wb] search.wb.ru responses: {len(search_responses)}")
        if search_responses:
            data = search_responses[0]
            products = data.get("data", {}).get("products", [])
            print(f"[wb] products in first response: {len(products)}")
            for item in products[:5]:
                print(
                    "  -",
                    item.get("name"),
                    "|",
                    item.get("salePriceU", 0) / 100,
                    "|",
                    f"https://www.wildberries.ru/catalog/{item.get('id')}/detail.aspx",
                )

        # DOM fallback: catalog grid cards
        dom_cards = page.eval_on_selector_all(
            "a[href*='/catalog/']",
            """els => els.map(a => ({
                title: (a.getAttribute('title') || (a.textContent || '').trim()).slice(0, 100),
                url: a.href
            })).filter(x => x.title)""",
        )
        print(f"[wb] DOM catalog links: {len(dom_cards)}")
        for card in dom_cards[:5]:
            print("   -", card["title"], "|", card["url"])

        context.storage_state(path="research/wb_state.json")
        browser.close()


if __name__ == "__main__":
    main()
