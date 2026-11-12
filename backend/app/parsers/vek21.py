"""21vek.by parser: products and vendors from the __NEXT_DATA__ state."""

from __future__ import annotations

import json
from datetime import datetime

from bs4 import BeautifulSoup

from app.parsers.base import BaseParser, Product

SEARCH_URL = "https://www.21vek.by/search/"

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
        cleaned = value.replace(" ", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None
    if isinstance(value, dict):
        for key in ("price", "min", "value"):
            parsed = _parse_price(value.get(key))
            if parsed is not None:
                return parsed
    return None


class TwentyOneVekParser(BaseParser):
    marketplace_id = "21vek"
    name = "21vek.by"
    version = "0.9.0"

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

        async with self._client() as client:
            for page in range(page_start, page_start + limit_pages):
                response = await client.get(
                    SEARCH_URL,
                    params={"term": query, "page": page},
                    headers=HEADERS,
                )
                response.raise_for_status()
                items = self._extract(response.text)
                if not items:
                    break
                added = self._add_products(products, seen, items, region)
                if not added:
                    break
                if page == page_start + limit_pages - 1:
                    self._truncated = True

        return self._apply_filters(products, filters)

    @staticmethod
    def _parse_state(html: str) -> dict | None:
        soup = BeautifulSoup(html, "html.parser")
        node = soup.find("script", id="__NEXT_DATA__")
        if node is None or not node.string:
            return None
        try:
            data = json.loads(node.string)
            return json.loads(data["props"]["pageProps"]["initialState"])
        except (KeyError, TypeError, json.JSONDecodeError):
            return None

    @classmethod
    def _extract(cls, html: str) -> list[dict]:
        state = cls._parse_state(html)
        items: list[dict] = []
        if state:
            products = state.get("searchResult", {}).get("products", {}) or {}
            cls._collect_products(products, items)
        if items:
            return items
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.select("a[href*='/products/']"):
            title = (link.get("title") or link.get_text(" ", strip=True)).strip()
            if not title:
                continue
            items.append({"title": title, "url": link.get("href"), "price": None})
        return items

    @classmethod
    def _collect_products(cls, obj: object, items: list[dict]) -> None:
        if isinstance(obj, dict):
            title = obj.get("name") or obj.get("title")
            url = obj.get("link") or obj.get("url")
            if isinstance(title, str) and title and url:
                items.append(
                    {"title": title, "url": url, "price": obj.get("price")}
                )
                return
            for value in obj.values():
                cls._collect_products(value, items)
        elif isinstance(obj, list):
            for value in obj:
                cls._collect_products(value, items)

    def _add_products(
        self, products: list[Product], seen: set[str], items: list[dict], region: str
    ) -> bool:
        now = datetime.now()
        added = 0
        for item in items:
            title = str(item.get("title", "")).strip()
            url = str(item.get("url", "")).strip()
            price = _parse_price(item.get("price"))
            if not title or not url:
                continue
            if url.startswith("/"):
                url = f"https://www.21vek.by{url}"
            if url in seen:
                continue
            seen.add(url)
            products.append(
                Product(
                    title=title,
                    price=price if price is not None else 0.0,
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
