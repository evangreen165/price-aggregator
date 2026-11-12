"""Query classifier: keyword categories, brand detection, per-category filters."""

from __future__ import annotations

import re

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
            {"key": "matrix_type", "label": "Тип матрицы", "options": ["IPS", "VA", "TN", "OLED"]},
            {
                "key": "built_in_speakers",
                "label": "Встроенные динамики",
                "options": ["Есть", "Нет"],
            },
            {"key": "curved", "label": "Изогнутый экран", "options": ["Да", "Нет"]},
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
            {
                "key": "storage",
                "label": "Объем памяти",
                "options": ["64 ГБ", "128 ГБ", "256 ГБ", "512 ГБ", "1 ТБ+"],
            },
            {
                "key": "color",
                "label": "Цвет",
                "options": ["Чёрный", "Белый", "Серебристый", "Синий", "Золотистый"],
            },
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
            {"key": "storage", "label": "Накопитель", "options": ["256 ГБ", "512 ГБ", "1 ТБ+"]},
        ],
    },
    "tv": {
        "keywords": ["телевизор", "tv", "led tv", "oled tv"],
        "filters": [
            {
                "key": "diagonal",
                "label": "Диагональ",
                "options": ["до 32\"", "43\"", "50–55\"", "65\"+"],
            },
            {"key": "resolution", "label": "Разрешение", "options": ["Full HD", "4K", "8K"]},
            {"key": "matrix_type", "label": "Тип матрицы", "options": ["LED", "OLED", "QLED"]},
            {"key": "smart_tv", "label": "Smart TV", "options": ["Да", "Нет"]},
        ],
    },
}

BRANDS: dict[str, dict] = {
    "samsung": {
        "categories": ["phones", "monitors", "tv"],
        "type_options": ["Смартфон", "Монитор", "Телевизор", "Планшет", "Ноутбук"],
    },
    "apple": {
        "categories": ["phones", "laptops", "tv"],
        "type_options": ["iPhone", "iPad", "MacBook", "Watch", "Apple TV"],
    },
    "xiaomi": {
        "categories": ["phones", "monitors", "laptops"],
        "type_options": ["Смартфон", "Монитор", "Ноутбук", "Планшет"],
    },
    "lg": {
        "categories": ["monitors", "tv", "phones"],
        "type_options": ["Монитор", "Телевизор", "Смартфон", "Холодильник"],
    },
    "asus": {
        "categories": ["laptops", "monitors"],
        "type_options": ["Ноутбук", "Монитор", "Материнская плата", "Видеокарта"],
    },
    "lenovo": {
        "categories": ["laptops", "monitors"],
        "type_options": ["Ноутбук", "Монитор", "Планшет"],
    },
    "hp": {
        "categories": ["laptops", "monitors"],
        "type_options": ["Ноутбук", "Монитор", "Принтер"],
    },
    "dell": {
        "categories": ["laptops", "monitors"],
        "type_options": ["Ноутбук", "Монитор"],
    },
    "sony": {
        "categories": ["phones", "tv", "monitors"],
        "type_options": ["Телефон", "Телевизор", "Монитор", "Наушники"],
    },
    "intel": {
        "categories": ["laptops", "monitors"],
        "type_options": ["Процессор", "Ноутбук", "Монитор"],
    },
    "amd": {
        "categories": ["laptops", "monitors"],
        "type_options": ["Процессор", "Ноутбук", "Монитор", "Видеокарта"],
    },
    "nvidia": {
        "categories": ["laptops", "monitors"],
        "type_options": ["Видеокарта", "Ноутбук", "Монитор"],
    },
}

DEFAULT_CATEGORY = "general"


def find_brand(query: str) -> str | None:
    """Return the first known brand found in the query, or None."""
    lowered = query.lower()
    for brand in BRANDS:
        if re.search(rf"\b{re.escape(brand)}\b", lowered):
            return brand
    return None


def classify(query: str) -> list[str]:
    """Return category ids matched by keywords and/or brand."""
    lowered = query.lower()
    categories: list[str] = []
    for category_id, definition in CATEGORIES.items():
        if any(keyword in lowered for keyword in definition["keywords"]):
            categories.append(category_id)
    brand = find_brand(query)
    if brand is not None:
        for category_id in BRANDS[brand]["categories"]:
            if category_id not in categories:
                categories.append(category_id)
    return categories or [DEFAULT_CATEGORY]


def filters_for_query(query: str) -> list[dict]:
    """Return merged filter definitions for a query (keyword + brand)."""
    merged: list[dict] = []
    seen: set[str] = set()
    for category_id in classify(query):
        for entry in CATEGORIES.get(category_id, {}).get("filters", []):
            if entry["key"] not in seen:
                seen.add(entry["key"])
                merged.append(entry)
    brand = find_brand(query)
    if brand is not None and "device_type" not in seen:
        merged.insert(
            0,
            {
                "key": "device_type",
                "label": "Тип устройства",
                "options": BRANDS[brand]["type_options"],
            },
        )
    return merged
