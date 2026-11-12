"""AliExpress parser: browser interception of aer-webapi/v2/recommend.

The site's own API is served through an X5 anti-bot layer (direct curl is
redirected to a punish page), so a headless browser session is used to
capture the JSON emitted by aer-webapi.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

from app.parsers.base import BaseParser, Product, launch_chromium

SEARCH_PAGE_URL = "https://aliexpress.ru/wholesale"
MAX_PAGES = 60


def _parse_price(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(" ", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None
    if isinstance(value, dict):
        for key in ("price", "salePrice", "value"):
            parsed = _parse_price(value.get(key))
            if parsed is not None:
                return parsed
    return None


class AliExpressParser(BaseParser):
    marketplace_id = "aliexpress"
    name = "AliExpress"
    version = "0.9.0"
    max_items = 3000

    async def search(
        self,
        query: str,
        region: str,
        limit_pages: int = 10,
        filters: dict[str, list[str]] | None = None,
        page_start: int = 1,
    ) -> list[Product]:
        products: list[Product] = []
        seen: set[str] = set()
        self._truncated = False

        for attempt in range(2):
            items = await self._browser_items(query, page_start, limit_pages)
            if items:
                self._add_products(products, seen, items, region)
                break
        if len(products) >= self.max_items:
            self._truncated = True

        return self._apply_filters(products, filters)

    async def _browser_items(self, query: str, page_start: int, limit_pages: int) -> list[dict]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return []
        try:
            async with async_playwright() as p:
                browser = await launch_chromium(p)
                if browser is None:
                    return []
                page = await browser.new_page()
                captured: list[dict] = []

                async def on_response(response) -> None:
                    if "aer-webapi" in response.url and "recommend" in response.url:
                        try:
                            body = await response.json()
                        except Exception:  # noqa: BLE001
                            return
                        captured.append(body)

                page.on("response", on_response)
                url = f"{SEARCH_PAGE_URL}?SearchText={quote(query)}&page={page_start}"
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                for _ in range(6):
                    await page.wait_for_timeout(2500)
                    try:
                        await page.mouse.wheel(0, 2500)
                    except Exception:  # noqa: BLE001
                        break
                await browser.close()
        except Exception:  # noqa: BLE001
            return []

        items: list[dict] = []
        for body in captured:
            data = body.get("data") or {}
            snippets = data.get("snippetsV2") or []
            if not snippets:
                continue
            for snippet in snippets:
                item = self._product_from_snippet(snippet)
                if item:
                    items.append(item)
        return items

    @staticmethod
    def _product_from_snippet(snippet: dict) -> dict | None:
        container = (snippet.get("snippetContainer") or {}).get("itemData") or {}
        pdp = (container.get("pdpInfo") or {}).get("preloadedData") or {}
        title = pdp.get("title") or pdp.get("name") or snippet.get("id")
        price = _parse_price(pdp.get("price") or pdp.get("salePrice"))
        product_id = snippet.get("id") or pdp.get("productId")
        if not title or price is None or not product_id:
            return None
        try:
            rating = float(pdp["rating"]) if pdp.get("rating") is not None else None
        except (TypeError, ValueError):
            rating = None
        return {
            "title": str(title),
            "price": price,
            "rating": rating,
            "url": f"https://aliexpress.ru/item/{product_id}.html",
        }

    def _add_products(
        self, products: list[Product], seen: set[str], items: list[dict], region: str
    ) -> bool:
        now = datetime.now()
        added = 0
        for item in items:
            title = str(item.get("title", "")).strip()
            url = str(item.get("url", "")).strip()
            price = item.get("price")
            if not title or not url or price is None or url in seen:
                continue
            seen.add(url)
            products.append(
                Product(
                    title=title,
                    price=float(price),
                    old_price=None,
                    currency="RUB",
                    url=url,
                    marketplace=self.marketplace_id,
                    region=region,
                    parsed_at=now,
                    rating=item.get("rating"),
                )
            )
            added += 1
        return added > 0
