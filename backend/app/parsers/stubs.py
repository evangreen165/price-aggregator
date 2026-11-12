"""Stub parsers for marketplaces with heavy anti-bot defenses (implemented later)."""

from __future__ import annotations

from app.parsers.base import BaseParser, Product


class OzonParser(BaseParser):
    marketplace_id = "ozon"
    name = "Ozon"
    version = "0.0.1"

    async def search(self, query: str, region: str, limit_pages: int = 3) -> list[Product]:
        return []


class WbParser(BaseParser):
    marketplace_id = "wb"
    name = "Wildberries"
    version = "0.0.1"

    async def search(self, query: str, region: str, limit_pages: int = 3) -> list[Product]:
        return []
