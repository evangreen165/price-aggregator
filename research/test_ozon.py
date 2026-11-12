"""Research: Ozon via Playwright (msedge, headful) — v2.

Scrolls, waits for product cards, intercepts composer-api responses.
"""

from __future__ import annotations

import json

from playwright.sync_api import sync_playwright

QUERY = "телевизор"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="msedge")
        context = browser.new_context(locale="ru-RU", viewport={"width": 1400, "height": 900})
        page = context.new_page()

        composer: list[str] = []

        def on_response(response) -> None:
            if "composer-api" in response.url:
                try:
                    body = response.text()
                    composer.append(body[:200])
                except Exception:
                    pass

        page.on("response", on_response)

        page.goto("https://www.ozon.ru/", timeout=90000)
        page.wait_for_timeout(12000)
        page.goto(f"https://www.ozon.ru/search/?text={QUERY}", timeout=90000)
        page.wait_for_timeout(5000)

        for _ in range(6):
            page.mouse.wheel(0, 1800)
            page.wait_for_timeout(1500)

        body_text = page.evaluate("() => document.body.innerText.slice(0, 400)")
        print("[ozon] body snippet:", body_text.replace("\n", " | ")[:300])

        print(f"[ozon] composer-api responses captured: {len(composer)}")
        for snippet in composer[:2]:
            print("   composer snippet:", snippet[:150])

        products = page.eval_on_selector_all(
            "a[href*='/product/']",
            """els => els.map(a => ({
                title: (a.getAttribute('title') || (a.textContent || '').trim()).slice(0, 120),
                url: a.href
            })).filter(x => x.title)""",
        )
        unique: list[dict] = []
        seen: set[str] = set()
        for item in products:
            if item["url"] not in seen:
                seen.add(item["url"])
                unique.append(item)
            if len(unique) >= 5:
                break
        print(f"[ozon] DOM product links: {len(products)} (unique {len(unique)})")
        for item in unique[:5]:
            print("  -", item["title"], "|", item["url"])

        context.storage_state(path="research/ozon_state.json")
        browser.close()


if __name__ == "__main__":
    main()
