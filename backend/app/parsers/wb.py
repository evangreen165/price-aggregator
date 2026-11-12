"""Wildberries parser: public search JSON API via curl_cffi."""

from __future__ import annotations

from datetime import datetime

from app.parsers.base import BaseParser, Product

WARM_URL = "https://www.wildberries.ru/"
SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v4/search"
DEST_PARAMS = "-1257783,1229390,1505371,1509256"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Origin": "https://www.wildberries.ru",
}


def _price_from_kopecks(value: object) -> float | None:
    try:
        return float(value) / 100.0
    except (TypeError, ValueError):
        return None


class WbParser(BaseParser):
    marketplace_id = "wb"
    name = "Wildberries"
    version = "0.5.0"

    def __init__(self, fetcher=None) -> None:
        super().__init__()
        self._fetcher = fetcher

    async def _fetch_json_from(self, session, url: str, params: dict) -> object | None:
        try:
            response = await session.get(url, params=params, headers=HEADERS, timeout=20)
        except Exception:  # noqa: BLE001
            return None
        if response.status_code != 200:
            return None
        try:
            return response.json()
        except ValueError:
            return None

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

        if self._fetcher is not None:
            session = self._fetcher
            for page in range(1, limit_pages + 1):
                data = await self._fetch_json_from(
                    session,
                    SEARCH_URL,
                    {"query": query, "dest": DEST_PARAMS, "resultset": "catalog", "page": page},
                )
                if data is None:
                    break
                added = self._add_products(products, seen, data, region)
                if not added:
                    break
                if page == limit_pages:
                    self._truncated = True
        else:
            from curl_cffi.requests import AsyncSession

            async with AsyncSession(impersonate="chrome") as session:
                await session.get(WARM_URL, headers=HEADERS, timeout=20)
                for page in range(1, limit_pages + 1):
                    data = await self._fetch_json_from(
                        session,
                        SEARCH_URL,
                        {"query": query, "dest": DEST_PARAMS, "resultset": "catalog", "page": page},
                    )
                    if data is None:
                        break
                    added = self._add_products(products, seen, data, region)
                    if not added:
                        break
                    if page == limit_pages:
                        self._truncated = True

        return self._apply_filters(products, filters)

    def _add_products(
        self, products: list[Product], seen: set[str], data: object, region: str
    ) -> bool:
        if not isinstance(data, dict):
            return False
        items = data.get("data", {}).get("products", [])
        if not isinstance(items, list):
            return False
        now = datetime.now()
        added = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("name", "")).strip()
            product_id = item.get("id")
            price = _price_from_kopecks(item.get("salePriceU"))
            if not title or product_id is None or price is None:
                continue
            url = f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"
            if url in seen:
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
