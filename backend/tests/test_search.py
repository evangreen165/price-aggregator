from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app
from app.parsers.base import BaseParser, Product


class FakeKufarParser(BaseParser):
    marketplace_id = "kufar"

    async def search(
        self,
        query: str,
        region: str,
        limit_pages: int = 10,
        filters: dict[str, list[str]] | None = None,
    ) -> list[Product]:
        return [
            Product(
                title=f"fake {query}",
                price=10.5,
                old_price=None,
                currency="BYN",
                url="https://example.com/item/1",
                marketplace=self.marketplace_id,
                region=region,
                parsed_at=datetime.now(),
            )
        ]


def test_search_endpoint_uses_selected_parsers(monkeypatch) -> None:
    def fake_get_parser(marketplace_id: str) -> BaseParser | None:
        if marketplace_id == "kufar":
            return FakeKufarParser()
        return None

    monkeypatch.setattr("app.main.get_parser", fake_get_parser)
    with TestClient(app) as client:
        response = client.post(
            "/api/search",
            json={"query": "монитор", "marketplaces": ["kufar", "onliner"], "region": "belarus"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["errors"] == {}
    results = body["results"]
    assert "kufar" in results
    assert results["kufar"][0]["title"] == "fake монитор"
    parsed_at = results["kufar"][0]["parsed_at"]
    assert "T" in parsed_at


def test_search_endpoint_records_parser_errors(monkeypatch) -> None:
    class FailingParser(BaseParser):
        marketplace_id = "onliner"

        async def search(
            self,
            query: str,
            region: str,
            limit_pages: int = 10,
            filters: dict[str, list[str]] | None = None,
        ) -> list[Product]:
            raise RuntimeError("boom")

    def fake_get_parser(marketplace_id: str) -> BaseParser | None:
        if marketplace_id == "onliner":
            return FailingParser()
        return None

    monkeypatch.setattr("app.main.get_parser", fake_get_parser)
    with TestClient(app) as client:
        response = client.post(
            "/api/search", json={"query": "x", "marketplaces": ["onliner"], "region": "belarus"}
        )
    assert response.status_code == 200
    body = response.json()
    assert body["results"]["onliner"] == []
    assert body["errors"]["onliner"] == "boom"


def test_search_endpoint_passes_filters_and_limit(monkeypatch) -> None:
    captured: dict = {}

    class CaptureParser(BaseParser):
        marketplace_id = "kufar"

        async def search(
            self,
            query: str,
            region: str,
            limit_pages: int = 10,
            filters: dict[str, list[str]] | None = None,
        ) -> list[Product]:
            captured["filters"] = filters
            captured["limit_pages"] = limit_pages
            return []

    def fake_get_parser(marketplace_id: str) -> BaseParser | None:
        return CaptureParser() if marketplace_id == "kufar" else None

    monkeypatch.setattr("app.main.get_parser", fake_get_parser)
    with TestClient(app) as client:
        response = client.post(
            "/api/search",
            json={
                "query": "samsung",
                "marketplaces": ["kufar"],
                "region": "belarus",
                "limit_pages": 5,
                "filters": {"brand": ["Samsung"]},
            },
        )
    assert response.status_code == 200
    assert captured["filters"] == {"brand": ["Samsung"]}
    assert captured["limit_pages"] == 5
