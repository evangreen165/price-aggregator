"""Onliner.by catalog parser: paginated JSON API + browser-rendered filters."""

from __future__ import annotations

from datetime import datetime

from app.parsers.base import BaseParser, Product, launch_chromium
from app.parsers.categories import classify

SEARCH_URL = "https://catalog.onliner.by/sdapi/catalog.api/search/products"
PAGE_LIMIT = 100
MAX_ITEMS = 5000

CATEGORY_PATHS = {
    "phones": "mobile",
    "laptops": "notebook",
    "tv": "tv",
    "tablets": "tabletpc",
}

_FILTER_JS = """els => els.map(g => {
  const caption = g.querySelector('.catalog-form__label-title');
  const options = Array.from(g.querySelectorAll('ul.catalog-form__checkbox-list span'))
      .map(s => (s.textContent || '').trim()).filter(Boolean);
  return { title: caption ? caption.textContent.trim() : null, options: options };
}).filter(g => g.title && g.options.length)"""


class OnlinerParser(BaseParser):
    marketplace_id = "onliner"
    name = "Onliner"
    version = "0.7.0"
    max_items = MAX_ITEMS

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

        sorts: list[str] = ["relevance"]
        if page_start == 1 and limit_pages >= 10:
            sorts = ["relevance", "price_asc", "price_desc"]

        async with self._client() as client:
            for sort in sorts:
                if len(products) >= self.max_items:
                    break
                for page in range(page_start, page_start + limit_pages):
                    params: dict[str, object] = {
                        "query": query,
                        "group": "1",
                        "limit": PAGE_LIMIT,
                        "page": page,
                    }
                    if sort != "relevance":
                        params["sort"] = sort
                    response = await client.get(SEARCH_URL, params=params)
                    response.raise_for_status()
                    body = response.json()
                    items = body.get("products", []) if isinstance(body, dict) else []
                    added = self._add_products(products, seen, items, region)
                    if not added:
                        break
                    if page == page_start + limit_pages - 1:
                        self._truncated = True
                    if len(products) >= self.max_items:
                        self._truncated = True
                        break
                if page_start == 1 and not self._truncated:
                    break

        return self._apply_filters(products, filters)

    async def fetch_filters(self, query: str) -> list[dict]:
        """Return real filter options from the rendered category page."""
        category = classify(query)[0]
        path = self.CATEGORY_PATHS.get(category)
        if not path:
            return []
        return await self._fetch_filters_from_page(f"https://catalog.onliner.by/{path}")

    async def _fetch_filters_from_page(self, url: str) -> list[dict]:
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
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:  # noqa: BLE001
                    pass
                data = await page.eval_on_selector_all(".catalog-form__group", _FILTER_JS)
                await browser.close()
        except Exception:  # noqa: BLE001
            return []
        merged: list[dict] = []
        for index, group in enumerate(data):
            merged.append(
                {
                    "key": f"group_{index}",
                    "label": group["title"],
                    "options": group["options"][:30],
                }
            )
            if len(merged) >= 15:
                break
        return merged

    def _add_products(
        self, products: list[Product], seen: set[str], items: list[dict], region: str
    ) -> bool:
        now = datetime.now()
        added = 0
        for item in items:
            title = str(item.get("full_name") or item.get("name") or "").strip()
            url = item.get("html_url") or item.get("url")
            price = self._min_price(item.get("prices"))
            if not title or not url or price is None or url in seen:
                continue
            seen.add(url)
            products.append(
                Product(
                    title=title,
                    price=price,
                    old_price=None,
                    currency="BYN",
                    url=url,
                    marketplace=self.marketplace_id,
                    region=region,
                    parsed_at=now,
                )
            )
            added += 1
        return added > 0

    @staticmethod
    def _min_price(prices: object) -> float | None:
        if not isinstance(prices, dict):
            return None
        try:
            return float(prices["price_min"]["amount"])
        except (KeyError, TypeError, ValueError):
            return None
