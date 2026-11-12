"""AliExpress parser: best-effort extraction from the wholesale search page."""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import quote

from curl_cffi import requests

from app.parsers.base import BaseParser, Product

SEARCH_URL = "https://www.aliexpress.com/w/wholesale-{query}.html"
MAX_PAGES = 60

HEADERS = {
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


def _parse_price(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return None
    return None


class AliExpressParser(BaseParser):
    marketplace_id = "aliexpress"
    name = "AliExpress"
    version = "0.8.0"
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
        pages = min(limit_pages, MAX_PAGES - page_start + 1)

        for page in range(page_start, page_start + pages):
            data = await self._fetch_page(query, page)
            if data is None:
                break
            added = self._add_products(products, seen, data, region)
            if not added:
                break
            if page == page_start + pages - 1:
                self._truncated = True
            if len(products) >= self.max_items:
                self._truncated = True
                break

        return self._apply_filters(products, filters)

    async def _fetch_page(self, query: str, page: int) -> object | None:
        url = SEARCH_URL.format(query=quote(query))
        try:
            with requests.Session(impersonate="chrome") as session:
                response = session.get(
                    url, params={"page": page}, headers=HEADERS, timeout=25
                )
        except Exception:  # noqa: BLE001
            return None
        if response.status_code != 200:
            return None
        return self._extract(response.text)

    def _extract(self, html: str) -> list[dict]:
        items: list[dict] = []
        blob = re.search(r"window\.runParams\s*=\s*(\{.*?\})\s*;\s*</script>", html, re.S)
        source = blob.group(1) if blob else html
        titles = re.findall(r'"subject"\s*:\s*"([^"]{5,200})"', source)
        prices = re.findall(r'"salePrice"\s*:\s*"(\d+(?:\.\d+)?)"', source)
        product_ids = re.findall(r'"productId"\s*:\s*"?(\d+)"?', source)
        detail_urls = re.findall(r'"productDetailUrl"\s*:\s*"([^"]+)"', source)
        count = min(len(titles), len(prices), len(product_ids))
        for index in range(count):
            items.append(
                {
                    "title": titles[index],
                    "price": prices[index],
                    "productId": product_ids[index],
                    "url": detail_urls[index] if index < len(detail_urls) else None,
                }
            )
        return items

    def _add_products(
        self, products: list[Product], seen: set[str], items: list[dict], region: str
    ) -> bool:
        now = datetime.now()
        added = 0
        for item in items:
            title = str(item.get("title", "")).strip()
            price = _parse_price(item.get("price"))
            product_id = item.get("productId")
            if not title or price is None or not product_id:
                continue
            url = (
                str(item.get("url"))
                if item.get("url")
                else f"https://www.aliexpress.com/item/{product_id}.html"
            )
            if url in seen:
                continue
            seen.add(url)
            products.append(
                Product(
                    title=title,
                    price=price,
                    old_price=None,
                    currency="USD",
                    url=url,
                    marketplace=self.marketplace_id,
                    region=region,
                    parsed_at=now,
                )
            )
            added += 1
        return added > 0
