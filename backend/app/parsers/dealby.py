"""Deal.by parser: best-effort extraction from the search page HTML."""

from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from app.parsers.base import BaseParser, Product

SEARCH_URL = "https://deal.by/search"

HEADERS = {
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

LINK_PATTERNS = ("/item/", "/goods/", "/product/")


class DealByParser(BaseParser):
    marketplace_id = "dealby"
    name = "Deal.by"
    version = "0.8.0"
    max_items = 5000

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

        async with self._client() as client:
            for page in range(page_start, page_start + limit_pages):
                response = await client.get(
                    SEARCH_URL,
                    params={"q": query, "page": page},
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
                if len(products) >= self.max_items:
                    self._truncated = True
                    break

        return self._apply_filters(products, filters)

    @staticmethod
    def _extract(html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        items: list[dict] = []
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            title = (link.get("title") or link.get_text(" ", strip=True) or "").strip()
            if not title or not any(pattern in href for pattern in LINK_PATTERNS):
                continue
            price = DealByParser._price_from_node(link)
            items.append({"title": title[:200], "url": href, "price": price})
        return items

    @staticmethod
    def _price_from_node(node) -> float | None:
        container = node.find_parent("div", class_=re.compile("item|card|product|goods")) or node
        text = container.get_text(" ", strip=True) if hasattr(container, "get_text") else ""
        match = re.search(r"(\d[\d\s]*[,.]?\d*)\s*(?:р\.|руб|BYN|₽)", text)
        if not match:
            return None
        try:
            return float(match.group(1).replace(" ", "").replace(",", "."))
        except ValueError:
            return None

    def _add_products(
        self, products: list[Product], seen: set[str], items: list[dict], region: str
    ) -> bool:
        now = datetime.now()
        added = 0
        for item in items:
            title = str(item.get("title", "")).strip()
            url = str(item.get("url", "")).strip()
            if not title or not url:
                continue
            if url.startswith("/"):
                url = f"https://deal.by{url}"
            if url in seen:
                continue
            seen.add(url)
            price = item.get("price")
            products.append(
                Product(
                    title=title,
                    price=float(price) if price is not None else 0.0,
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
