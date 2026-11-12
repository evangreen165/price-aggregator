"""Example parser plugin: returns fake data, performs no network calls."""

from __future__ import annotations

from app.plugins import hookimpl


class ExampleParser:
    """Minimal parser used to exercise the plugin contract."""

    marketplace_id = "example"
    name = "Example Parser"
    version = "0.1.0"

    def search(self, query: str) -> list[dict]:
        return [
            {
                "id": "example-1",
                "title": f"Example result for {query}",
                "price": 1999.0,
                "currency": "USD",
                "url": "https://example.com/item/1",
                "marketplace": self.marketplace_id,
            }
        ]


@hookimpl
def register_parser():
    return "example", ExampleParser
