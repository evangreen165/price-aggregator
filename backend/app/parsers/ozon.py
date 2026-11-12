"""Ozon parser: composer API with Playwright browser fallback."""

from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import quote

from app.parsers.base import BaseParser, Product, launch_chromium

WARM_URL = "https://www.ozon.ru/"
COMPOSER_URL = "https://www.ozon.ru/api/composer-api.bx/page/json/v2"
SEARCH_PAGE_URL = "https://www.ozon.ru/search/"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Origin": "https://www.ozon.ru",
}

_EVALUATE_JS = """
() => {
  if (window.__NUXT__ && window.__NUXT__.data) {
    return JSON.stringify(window.__NUXT__);
  }
  const node = document.querySelector('script#__NEXT_DATA__');
  if (node && node.textContent) {
    return node.textContent;
  }
  return null;
}
"""


def _parse_price(value: object) -> float | None:
    if isinstance(value, dict):
        for key in ("price", "cardPrice", "oldPrice"):
            parsed = _parse_price(value.get(key))
            if parsed is not None:
                return parsed
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(" ", "").replace("\u00a0", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


class OzonParser(BaseParser):
    marketplace_id = "ozon"
    name = "Ozon"
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
        data = await self._curl_search_data(query)
        if data is None:
            data = await self._browser_search_data(query)
        if data is None:
            return []
        return self._apply_filters(self._extract(data, region), filters)

    async def _curl_search_data(self, query: str) -> object | None:
        params = {"url": f"/search/?text={query}"}
        if self._fetcher is not None:
            return await self._fetch_json_from(self._fetcher, COMPOSER_URL, params)
        from curl_cffi.requests import AsyncSession

        async with AsyncSession(impersonate="chrome") as session:
            await session.get(WARM_URL, headers=HEADERS, timeout=20)
            return await self._fetch_json_from(session, COMPOSER_URL, params)

    async def _browser_search_data(self, query: str) -> object | None:
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
                await page.goto(
                    f"{SEARCH_PAGE_URL}?text={quote(query)}",
                    timeout=60000,
                    wait_until="domcontentloaded",
                )
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:  # noqa: BLE001
                    pass
                text = await page.evaluate(_EVALUATE_JS)
                await browser.close()
                if not text:
                    return None
                try:
                    return json.loads(text)
                except ValueError:
                    return None
        except Exception:  # noqa: BLE001
            return None

    def _extract(self, data: object, region: str) -> list[Product]:
        products: list[Product] = []
        now = datetime.now()
        for candidate in self._walk(data):
            title = str(candidate.get("title") or candidate.get("name") or "").strip()
            price = _parse_price(candidate.get("price"))
            product_id = candidate.get("skuId") or candidate.get("id")
            if not title or price is None or product_id is None:
                continue
            products.append(
                Product(
                    title=title,
                    price=price,
                    old_price=None,
                    currency="BYN",
                    url=f"https://www.ozon.ru/product/{product_id}",
                    marketplace=self.marketplace_id,
                    region=region,
                    parsed_at=now,
                )
            )
        return products

    @classmethod
    def _walk(cls, obj: object) -> list[dict]:
        found: list[dict] = []
        if isinstance(obj, dict):
            if cls._is_product(obj):
                found.append(obj)
            for value in obj.values():
                found.extend(cls._walk(value))
        elif isinstance(obj, list):
            for item in obj:
                found.extend(cls._walk(item))
        elif isinstance(obj, str):
            try:
                found.extend(cls._walk(json.loads(obj)))
            except ValueError:
                return found
        return found

    @staticmethod
    def _is_product(obj: dict) -> bool:
        title = obj.get("title") or obj.get("name")
        has_identity = "price" in obj or "cardPrice" in obj or "skuId" in obj or "id" in obj
        return isinstance(title, str) and bool(title.strip()) and has_identity
