"""Kufar.by parser: paginated extraction from the embedded __NEXT_DATA__ JSON."""

from __future__ import annotations

import json
from datetime import datetime

from bs4 import BeautifulSoup

from app.parsers.base import BaseParser, Product

SEARCH_URL = "https://www.kufar.by/l"
RENDERED_API_URL = "https://api.kufar.by/search-api/v2/search/rendered"
PAGE_SIZE = 50


def _price_from_kopecks(value: object) -> float | None:
    try:
        return float(value) / 100.0
    except (TypeError, ValueError):
        return None


class KufarParser(BaseParser):
    marketplace_id = "kufar"
    name = "Kufar"
    version = "0.3.0"

    async def search(self, query: str, region: str, limit_pages: int = 3) -> list[Product]:
        products: list[Product] = []
        seen: set[str] = set()

        async with self._client() as client:
            response = await client.get(SEARCH_URL, params={"query": query})
            response.raise_for_status()
            listing = self._parse_listing(response.text)
            if listing is None:
                return products

            tokens = {
                entry["num"]: entry["token"]
                for entry in listing.get("pagination", [])
                if entry.get("token")
            }
            self._add_products(products, seen, listing.get("ads", []), region)

            for page in range(2, limit_pages + 1):
                token = tokens.get(page)
                if not token:
                    break
                api_response = await client.get(
                    RENDERED_API_URL,
                    params={"query": query, "size": PAGE_SIZE, "lang": "ru", "cursor": token},
                )
                if api_response.status_code != 200:
                    break
                try:
                    ads = api_response.json().get("ads", [])
                except ValueError:
                    break
                if not self._add_products(products, seen, ads, region):
                    break

        return products

    @staticmethod
    def _parse_listing(html: str) -> dict | None:
        soup = BeautifulSoup(html, "html.parser")
        node = soup.find("script", id="__NEXT_DATA__")
        if node is None or not node.string:
            return None
        try:
            data = json.loads(node.string)
            return data["props"]["initialState"]["listing"]
        except (KeyError, TypeError, json.JSONDecodeError):
            return None

    def _add_products(
        self, products: list[Product], seen: set[str], ads: list[dict], region: str
    ) -> bool:
        now = datetime.now()
        added = 0
        for ad in ads:
            title = str(ad.get("subject", "")).strip()
            url = ad.get("ad_link")
            price = _price_from_kopecks(ad.get("price_byn"))
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
                    region=self._region_of(ad) or region,
                    parsed_at=now,
                )
            )
            added += 1
        return added > 0

    @staticmethod
    def _region_of(ad: dict) -> str | None:
        for param in ad.get("ad_parameters", []):
            if param.get("p") == "region":
                value = param.get("vl")
                return str(value).strip() if value else None
        return None
