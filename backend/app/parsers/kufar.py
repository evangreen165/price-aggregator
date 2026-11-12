"""Kufar.by parser: cursor-based deep pagination."""

from __future__ import annotations

import base64
import json
from datetime import datetime

from bs4 import BeautifulSoup

from app.parsers.base import BaseParser, Product

SEARCH_URL = "https://www.kufar.by/l"
RENDERED_API_URL = "https://api.kufar.by/search-api/v2/search/rendered"
PAGE_SIZE = 50
MAX_ITEMS = 5000


def _price_from_kopecks(value: object) -> float | None:
    try:
        return float(value) / 100.0
    except (TypeError, ValueError):
        return None


class KufarParser(BaseParser):
    marketplace_id = "kufar"
    name = "Kufar"
    version = "0.8.0"
    max_items = MAX_ITEMS

    async def search(
        self,
        query: str,
        region: str,
        limit_pages: int = 10,
        filters: dict[str, list[str]] | None = None,
        page_start: int = 1,
        cursor: str | None = None,
    ) -> list[Product]:
        products: list[Product] = []
        seen: set[str] = set()
        self._truncated = False
        self._next_cursor = None

        async with self._client() as client:
            if cursor:
                try:
                    payload = json.loads(base64.b64decode(cursor))
                    pit = payload.get("pit")
                    page_start = int(payload.get("p", page_start))
                except (ValueError, TypeError, json.JSONDecodeError):
                    pit = None
            else:
                response = await client.get(SEARCH_URL, params={"query": query})
                response.raise_for_status()
                listing = self._parse_listing(response.text)
                if listing is None:
                    return products
                pit = self._search_id(listing.get("pagination", []))
                if page_start == 1:
                    self._add_products(products, seen, listing.get("ads", []), region)

            for page in range(page_start, page_start + limit_pages):
                if page == 1:
                    continue
                if pit is None:
                    break
                api_response = await client.get(
                    RENDERED_API_URL,
                    params={
                        "query": query,
                        "size": PAGE_SIZE,
                        "lang": "ru",
                        "cursor": self._make_token(pit, page),
                    },
                )
                if api_response.status_code != 200:
                    break
                try:
                    ads = api_response.json().get("ads", [])
                except ValueError:
                    break
                added = self._add_products(products, seen, ads, region)
                if not added:
                    break
                if page == page_start + limit_pages - 1:
                    self._truncated = True
                if len(products) >= self.max_items:
                    self._truncated = True
                    break

        if self._truncated and pit:
            self._next_cursor = self._make_token(pit, page_start + limit_pages)
        return self._apply_filters(products, filters)

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

    @staticmethod
    def _search_id(pagination: list[dict]) -> str | None:
        for entry in pagination:
            token = entry.get("token")
            if not token:
                continue
            try:
                payload = json.loads(base64.b64decode(token))
                return payload.get("pit")
            except (ValueError, TypeError, json.JSONDecodeError):
                continue
        return None

    @staticmethod
    def _make_token(search_id: str, page: int) -> str:
        payload = {"t": "abs", "f": True, "p": page, "pit": search_id}
        raw = json.dumps(payload, separators=(",", ":"))
        return base64.b64encode(raw.encode()).decode()

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
