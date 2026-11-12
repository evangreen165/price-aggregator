from fastapi.testclient import TestClient

from app.main import app
from app.parsers.categories import classify, filters_for_query


def test_classify_keywords() -> None:
    assert classify("монитор 27 дюймов") == "monitors"
    assert classify("display 24") == "monitors"
    assert classify("iphone 15 pro") == "phones"
    assert classify("смартфон samsung") == "phones"
    assert classify("ноутбук asus") == "laptops"
    assert classify("совершенно непонятный запрос") == "general"


def test_monitor_filters() -> None:
    filters = filters_for_query("монитор")
    keys = {entry["key"] for entry in filters}
    assert {"diagonal", "resolution", "refresh_rate"} <= keys
    assert "Разрешение" in {entry["label"] for entry in filters}


def test_phone_filters() -> None:
    filters = filters_for_query("iphone")
    assert filters
    assert {"brand", "os"} <= {entry["key"] for entry in filters}


def test_general_has_no_filters() -> None:
    assert filters_for_query("что-то непонятное") == []


def test_filters_endpoint_for_monitor() -> None:
    with TestClient(app) as client:
        response = client.get("/api/filters", params={"query": "монитор"})
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "monitors"
    assert any(entry["label"] == "Разрешение" for entry in body["filters"])


def test_filters_endpoint_for_phone_and_empty() -> None:
    with TestClient(app) as client:
        phone_response = client.get("/api/filters", params={"query": "iphone"})
        empty_response = client.get("/api/filters", params={"query": ""})
    assert phone_response.json()["category"] == "phones"
    assert phone_response.json()["filters"]
    assert empty_response.json()["category"] == "general"
    assert empty_response.json()["filters"] == []
