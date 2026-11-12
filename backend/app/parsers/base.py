"""Base classes for marketplace parsers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import ClassVar

import httpx

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}
DEFAULT_TIMEOUT = httpx.Timeout(20.0)


@dataclass
class Product:
    title: str
    price: float
    old_price: float | None
    currency: str
    url: str
    marketplace: str
    region: str
    parsed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["parsed_at"] = self.parsed_at.isoformat()
        return data


class BaseParser(ABC):
    marketplace_id: ClassVar[str] = ""
    name: ClassVar[str] = ""
    version: ClassVar[str] = "0.1.0"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._injected_client = client

    @asynccontextmanager
    async def _client(self) -> AsyncIterator[httpx.AsyncClient]:
        if self._injected_client is not None:
            yield self._injected_client
            return
        async with httpx.AsyncClient(
            headers=DEFAULT_HEADERS, follow_redirects=True, timeout=DEFAULT_TIMEOUT
        ) as client:
            yield client

    @abstractmethod
    async def search(self, query: str, region: str, limit_pages: int = 3) -> list[Product]:
        raise NotImplementedError
