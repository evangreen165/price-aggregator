"""Onliner.by catalog parser: paginated JSON API."""

from __future__ import annotations

from datetime import datetime

from app.parsers.base import BaseParser, Product

SEARCH_URL = "https://catalog.onliner.by/sdapi/catalog.api/search/products"
PAGE_LIMIT = 100


class OnlinerParser(BaseParser):
    marketplace_id = "onliner"
    name = "Onliner"
    version = "0.3.0"

    async def search(
        self,
        query: str,
        region: str,
        limit_pages: int = 10,
        filters: dict[str, list[str]] | None = None,
    ) -> list[Product]:
        products: list[Product] = []
        seen: set[str] = set()
        self._truncated = False

        async with self._client() as client:
            for page in range(1, limit_pages + 1):
                response = await client.get(
                    SEARCH_URL,
                    params={"query": query, "group": "1", "limit": PAGE_LIMIT, "page": page},
                )
                response.raise_for_status()
                body = response.json()
                items = body.get("products", []) if isinstance(body, dict) else []
                added = self._add_products(products, seen, items, region)
                if not added:
                    break
                if page == limit_pages:
                    self._truncated = True

        return self._apply_filters(products, filters)

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
