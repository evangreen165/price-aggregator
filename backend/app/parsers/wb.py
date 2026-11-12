"""Wildberries parser: public search JSON API, browser fallback via Playwright."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

from app.parsers.base import BaseParser, Product, launch_chromium

WARM_URL = "https://www.wildberries.ru/"
SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v4/search"
SEARCH_PAGE_URL = "https://www.wildberries.ru/catalog/0/search.aspx"
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
    version = "0.6.0"

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

        if not await self._curl_search(query, region, limit_pages, products, seen):
            await self._browser_search(query, region, products, seen)

        return self._apply_filters(products, filters)

    async def _curl_search(
        self, query: str, region: str, limit_pages: int, products: list[Product], seen: set[str]
    ) -> bool:
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
            return bool(products)

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
        return bool(products)

    async def _browser_search(
        self, query: str, region: str, products: list[Product], seen: set[str]
    ) -> None:
        data = await self._fetch_browser_search_data(query)
        if data is not None:
            self._add_products(products, seen, data, region)

    async def _fetch_browser_search_data(self, query: str) -> object | None:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return None
        try:
            async with async_playwright() as p:
                browser = await launch_chromium(p)
                if browser is None:
                    return None
                page = await browser.new_page()
                captured: list[object] = []

                async def on_response(response) -> None:
                    if "search.wb.ru" in response.url:
                        try:
                            captured.append(await response.json())
                        except Exception:  # noqa: BLE001
                            pass

                page.on("response", on_response)
                await page.goto(
                    f"{SEARCH_PAGE_URL}?search={quote(query)}",
                    timeout=60000,
                    wait_until="domcontentloaded",
                )
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:  # noqa: BLE001
                    pass
                await browser.close()
                return captured[0] if captured else None
        except Exception:  # noqa: BLE001
            return None

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
