"""Onliner.by catalog parser: uses the catalog search JSON API."""

from __future__ import annotations

from datetime import datetime

from app.parsers.base import BaseParser, Product

SEARCH_URL = "https://catalog.onliner.by/sdapi/catalog.api/search/products"


class OnlinerParser(BaseParser):
    marketplace_id = "onliner"
    name = "Onliner"
    version = "0.2.0"

    async def search(self, query: str, region: str) -> list[Product]:
        response = await self._get(SEARCH_URL, params={"query": query, "group": "1"})
        response.raise_for_status()
        return self._extract(response.json(), region)

    def _extract(self, data: object, region: str) -> list[Product]:
        items = data.get("products", []) if isinstance(data, dict) else []
        if not isinstance(items, list):
            return []

        now = datetime.now()
        products: list[Product] = []
        for item in items:
            title = str(item.get("full_name") or item.get("name") or "").strip()
            url = item.get("html_url") or item.get("url")
            price = self._min_price(item.get("prices"))
            if not title or not url or price is None:
                continue
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
        return products

    @staticmethod
    def _min_price(prices: object) -> float | None:
        if not isinstance(prices, dict):
            return None
        try:
            return float(prices["price_min"]["amount"])
        except (KeyError, TypeError, ValueError):
            return None
