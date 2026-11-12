from fastapi.testclient import TestClient

from app.main import app
from app.parsers.categories import classify, filters_for_query, find_brand


def test_classify_keywords() -> None:
    assert classify("монитор 27 дюймов") == ["monitors"]
    assert "monitors" in classify("display 24")
    assert "phones" in classify("iphone 15 pro")
    assert "laptops" in classify("ноутбук asus")
    assert classify("совершенно непонятный запрос") == ["general"]


def test_find_brand() -> None:
    assert find_brand("samsung galaxy") == "samsung"
    assert find_brand("iphone apple") == "apple"
    assert find_brand("офигеть не знаю что это") is None


def test_classify_by_brand_returns_possible_categories() -> None:
    categories = classify("samsung")
    assert "phones" in categories
    assert "monitors" in categories
    assert "tv" in categories


def test_classify_keyword_and_brand_combine() -> None:
    categories = classify("монитор samsung")
    assert "monitors" in categories
    assert categories[0] == "monitors"


def test_samsung_brand_filters_include_device_type() -> None:
    filters = filters_for_query("samsung")
    assert filters
    assert filters[0]["key"] == "device_type"
    assert filters[0]["label"] == "Тип устройства"
    assert "Монитор" in filters[0]["options"]
    assert "Смартфон" in filters[0]["options"]
    assert "Телевизор" in filters[0]["options"]


def test_monitor_filters_extended() -> None:
    filters = filters_for_query("монитор")
    keys = {entry["key"] for entry in filters}
    expected = {
        "diagonal",
        "resolution",
        "refresh_rate",
        "matrix_type",
        "built_in_speakers",
        "curved",
    }
    assert expected <= keys
    assert "Тип матрицы" in {entry["label"] for entry in filters}


def test_phone_filters_extended() -> None:
    filters = filters_for_query("iphone")
    keys = {entry["key"] for entry in filters}
    assert {"brand", "os", "storage", "color"} <= keys


def test_tablet_keyword_classifies() -> None:
    assert classify("планшет") == ["tablets"]
    assert "tablets" in classify("ipad air")


def test_tablet_filters() -> None:
    filters = filters_for_query("планшет")
    keys = {entry["key"] for entry in filters}
    assert {"brand", "storage", "diagonal"} <= keys
    labels = {entry["label"] for entry in filters}
    assert "Диагональ экрана" in labels


def test_general_has_base_filters() -> None:
    filters = filters_for_query("что-то непонятное")
    keys = {entry["key"] for entry in filters}
    assert {"price_range", "brand"} <= keys
    price_filter = next(entry for entry in filters if entry["key"] == "price_range")
    assert price_filter["label"] == "Цена от/до"


def test_filters_endpoint_returns_categories_list() -> None:
    with TestClient(app) as client:
        monitor = client.get("/api/filters", params={"query": "монитор"}).json()
        samsung = client.get("/api/filters", params={"query": "samsung"}).json()
        empty = client.get("/api/filters", params={"query": ""}).json()
    assert monitor["category"] == "monitors"
    assert monitor["categories"] == ["monitors"]
    assert any(entry["label"] == "Разрешение" for entry in monitor["filters"])
    assert "monitors" in samsung["categories"]
    assert samsung["filters"][0]["label"] == "Тип устройства"
    assert empty["category"] == "general"
    assert empty["categories"] == ["general"]
    assert any(entry["key"] == "price_range" for entry in empty["filters"])


def test_tablet_filters_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/filters", params={"query": "планшет"})
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "tablets"
    assert any(entry["label"] == "Диагональ экрана" for entry in body["filters"])


def test_proxy_rejects_invalid_urls() -> None:
    with TestClient(app) as client:
        response = client.get("/proxy", params={"url": "javascript:alert(1)"})
    assert response.status_code == 400
