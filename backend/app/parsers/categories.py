"""Lightweight query classifier and per-category filter definitions."""

from __future__ import annotations

CATEGORIES: dict[str, dict] = {
    "monitors": {
        "keywords": ["монитор", "экран", "дисплей", "display", "monitor"],
        "filters": [
            {"key": "diagonal", "label": "Диагональ", "options": ["до 24\"", "24–27\"", "27\"+"]},
            {
                "key": "resolution",
                "label": "Разрешение",
                "options": ["HD", "Full HD", "2K", "4K"],
            },
            {
                "key": "refresh_rate",
                "label": "Частота обновления",
                "options": ["60 Гц", "144 Гц", "165 Гц+"],
            },
        ],
    },
    "phones": {
        "keywords": ["телефон", "смартфон", "iphone", "айфон", "phone"],
        "filters": [
            {
                "key": "brand",
                "label": "Бренд",
                "options": ["Apple", "Samsung", "Xiaomi", "Huawei"],
            },
            {"key": "os", "label": "ОС", "options": ["iOS", "Android"]},
        ],
    },
    "laptops": {
        "keywords": ["ноутбук", "laptop", "ultrabook", "макбук"],
        "filters": [
            {
                "key": "brand",
                "label": "Бренд",
                "options": ["Apple", "Asus", "Lenovo", "HP", "Dell"],
            },
            {"key": "ram", "label": "Оперативная память", "options": ["8 ГБ", "16 ГБ", "32 ГБ+"]},
        ],
    },
}

DEFAULT_CATEGORY = "general"


def classify(query: str) -> str:
    """Map a free-form query to a category id by keyword matching."""
    lowered = query.lower()
    for category_id, definition in CATEGORIES.items():
        if any(keyword in lowered for keyword in definition["keywords"]):
            return category_id
    return DEFAULT_CATEGORY


def filters_for_query(query: str) -> list[dict]:
    """Return the filter definitions available for a query."""
    category_id = classify(query)
    return CATEGORIES.get(category_id, {}).get("filters", [])
