"""Kufar.by parser: extracts product data from the embedded __NEXT_DATA__ JSON."""

from __future__ import annotations

import json
from datetime import datetime

from bs4 import BeautifulSoup

from app.parsers.base import BaseParser, Product

SEARCH_URL = "https://www.kufar.by/l"


def _price_from_kopecks(value: object) -> float | None:
    try:
        return float(value) / 100.0
    except (TypeError, ValueError):
        return None


class KufarParser(BaseParser):
    marketplace_id = "kufar"
    name = "Kufar"
    version = "0.2.0"

    async def search(self, query: str, region: str) -> list[Product]:
        response = await self._get(SEARCH_URL, params={"query": query})
        response.raise_for_status()
        return self._extract(response.text, region)

    def _extract(self, html: str, region: str) -> list[Product]:
        soup = BeautifulSoup(html, "html.parser")
        node = soup.find("script", id="__NEXT_DATA__")
        if node is None or not node.string:
            return []
        try:
            data = json.loads(node.string)
            ads = data["props"]["initialState"]["listing"]["ads"]
        except (KeyError, TypeError, json.JSONDecodeError):
            return []

        now = datetime.now()
        products: list[Product] = []
        for ad in ads:
            title = str(ad.get("subject", "")).strip()
            url = ad.get("ad_link")
            price = _price_from_kopecks(ad.get("price_byn"))
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
                    region=self._region_of(ad) or region,
                    parsed_at=now,
                )
            )
        return products

    @staticmethod
    def _region_of(ad: dict) -> str | None:
        for param in ad.get("ad_parameters", []):
            if param.get("p") == "region":
                value = param.get("vl")
                return str(value).strip() if value else None
        return None
