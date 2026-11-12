"""Registry of available marketplace parsers."""

from __future__ import annotations

from app.parsers.base import BaseParser, Product
from app.parsers.kufar import KufarParser
from app.parsers.onliner import OnlinerParser
from app.parsers.vek21 import TwentyOneVekParser

PARSERS: dict[str, type[BaseParser]] = {
    KufarParser.marketplace_id: KufarParser,
    OnlinerParser.marketplace_id: OnlinerParser,
    TwentyOneVekParser.marketplace_id: TwentyOneVekParser,
}


def get_parser(marketplace_id: str) -> BaseParser | None:
    """Return a fresh parser instance for a marketplace id, or None."""
    parser_class = PARSERS.get(marketplace_id)
    return parser_class() if parser_class is not None else None


def list_parsers() -> list[dict]:
    return [
        {"marketplace_id": cls.marketplace_id, "name": cls.name, "version": cls.version}
        for cls in PARSERS.values()
    ]


__all__ = ["PARSERS", "Product", "get_parser", "list_parsers"]
