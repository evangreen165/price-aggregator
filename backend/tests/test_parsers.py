import asyncio
import base64
import json

import httpx
import pytest

from app.parsers import PARSERS, get_parser, list_parsers
from app.parsers.base import MarketplaceBlockedError, Product
from app.parsers.kufar import KufarParser
from app.parsers.onliner import OnlinerParser
from app.parsers.ozon import OzonParser
from app.parsers.wb import WbParser


def _kufar_token(search_id: str, page: int) -> str:
    payload = {"t": "abs", "f": True, "p": page, "pit": search_id}
    raw = json.dumps(payload, separators=(",", ":"))
    return base64.b64encode(raw.encode()).decode()


KUFAR_HTML = """
<html><body><script id="__NEXT_DATA__" type="application/json">
{"props":{"initialState":{"listing":{
  "ads":[
    {"subject":"Монитор 27 IPS", "ad_link":"https://www.kufar.by/item/1",
     "price_byn":41999, "currency":"BYR", "ad_parameters":[{"p":"region","vl":"Минск"}]},
    {"subject":"Монитор 24", "ad_link":"https://www.kufar.by/item/2",
     "price_byn":24900, "currency":"BYR", "ad_parameters":[]}
  ],
  "pagination":[
    {"num":1,"token":null},
    {"num":2,"token":"%s"},
    {"num":3,"token":"%s"}
  ]
}}}}
</script></body></html>
""" % (_kufar_token("PIT1", 2), _kufar_token("PIT1", 3))

ONLINER_ITEMS = [
    {
        "full_name": "ASUS ROG Swift OLED PG34WCDN",
        "html_url": "https://catalog.onliner.by/display/asus/pg34wcdn",
        "prices": {"price_min": {"amount": "6642.68", "currency": "BYN"}},
    },
    {
        "full_name": "Samsung Essential G3",
        "html_url": "https://catalog.onliner.by/display/samsung/le24gh310",
        "prices": {"price_min": {"amount": "465.26", "currency": "BYN"}},
    },
]


def test_kufar_extracts_listing_ads() -> None:
    parser = KufarParser()
    listing = parser._parse_listing(KUFAR_HTML)
    products: list = []
    parser._add_products(products, set(), listing["ads"], "belarus")
    assert len(products) == 2
    first = products[0]
    assert first.title == "Монитор 27 IPS"
    assert first.price == 419.99
    assert first.currency == "BYN"
    assert first.marketplace == "kufar"
    assert first.region == "Минск"
    assert products[1].region == "belarus"


def _kufar_handler(html: str, extra_pages: dict[int, list[dict]]):
    def handler(request: httpx.Request) -> httpx.Response:
        if "search-api" in str(request.url):
            cursor = request.url.params.get("cursor")
            page = None
            try:
                page = json.loads(base64.b64decode(cursor)).get("p")
            except (ValueError, TypeError, json.JSONDecodeError):
                page = None
            return httpx.Response(200, json={"ads": extra_pages.get(page, [])})
        return httpx.Response(200, text=html)

    return handler


def test_kufar_search_collects_pages_and_dedupes() -> None:
    ad_c = {
        "subject": "Монитор 32 OLED",
        "ad_link": "https://www.kufar.by/item/3",
        "price_byn": 89900,
        "ad_parameters": [],
    }
    handler = _kufar_handler(KUFAR_HTML, {2: [ad_c, ad_c], 3: []})
    parser = KufarParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    products = asyncio.run(parser.search("монитор", "belarus", limit_pages=3))
    assert len(products) == 3
    assert products[2].title == "Монитор 32 OLED"
    assert products[2].price == 899.0


def test_kufar_search_stops_when_no_new_items() -> None:
    handler = _kufar_handler(KUFAR_HTML, {2: [], 3: []})
    parser = KufarParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    products = asyncio.run(parser.search("монитор", "belarus", limit_pages=3))
    assert len(products) == 2


def test_kufar_search_respects_limit_pages() -> None:
    handler = _kufar_handler(KUFAR_HTML, {})
    parser = KufarParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    products = asyncio.run(parser.search("монитор", "belarus", limit_pages=1))
    assert len(products) == 2


def test_kufar_search_applies_filters() -> None:
    ad_samsung = {
        "subject": "Телевизор Samsung 55",
        "ad_link": "https://www.kufar.by/item/9",
        "price_byn": 199900,
        "ad_parameters": [],
    }
    ad_lg = {
        "subject": "Телевизор LG 43",
        "ad_link": "https://www.kufar.by/item/10",
        "price_byn": 149900,
        "ad_parameters": [],
    }
    handler = _kufar_handler(KUFAR_HTML, {2: [ad_samsung, ad_lg]})
    parser = KufarParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    products = asyncio.run(
        parser.search("телевизор", "belarus", limit_pages=2, filters={"brand": ["Samsung"]})
    )
    assert len(products) == 1
    assert "Samsung" in products[0].title


def test_onliner_extracts_items() -> None:
    parser = OnlinerParser()
    products: list = []
    parser._add_products(products, set(), ONLINER_ITEMS, "belarus")
    assert len(products) == 2
    assert products[0].title == "ASUS ROG Swift OLED PG34WCDN"
    assert products[0].price == 6642.68
    assert products[0].marketplace == "onliner"


def _onliner_handler(items_by_page: dict[int, list[dict]]):
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        return httpx.Response(200, json={"products": items_by_page.get(page, [])})

    return handler


def test_onliner_search_collects_pages() -> None:
    third = {
        "full_name": "LG UltraGear 27",
        "html_url": "https://catalog.onliner.by/display/lg/27gn800",
        "prices": {"price_min": {"amount": "990.0", "currency": "BYN"}},
    }
    handler = _onliner_handler({1: ONLINER_ITEMS, 2: [third]})
    parser = OnlinerParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    products = asyncio.run(parser.search("монитор", "belarus", limit_pages=3))
    assert len(products) == 3
    assert products[2].title == "LG UltraGear 27"


def test_onliner_search_applies_filters() -> None:
    handler = _onliner_handler({1: ONLINER_ITEMS})
    parser = OnlinerParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    products = asyncio.run(
        parser.search("монитор", "belarus", limit_pages=2, filters={"brand": ["Samsung"]})
    )
    assert len(products) == 1
    assert "Samsung" in products[0].title


def test_onliner_search_stops_on_empty_page() -> None:
    handler = _onliner_handler({1: ONLINER_ITEMS, 2: []})
    parser = OnlinerParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    products = asyncio.run(parser.search("монитор", "belarus", limit_pages=3))
    assert len(products) == 2


def test_onliner_search_marks_truncated_at_limit() -> None:
    third = {
        "full_name": "LG UltraGear 27",
        "html_url": "https://catalog.onliner.by/display/lg/27gn800",
        "prices": {"price_min": {"amount": "990.0", "currency": "BYN"}},
    }
    handler = _onliner_handler({1: ONLINER_ITEMS, 2: [third]})
    parser = OnlinerParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    asyncio.run(parser.search("монитор", "belarus", limit_pages=2))
    assert parser._truncated is True


WB_JSON = {
    "data": {
        "products": [
            {"id": 1001, "name": "Телевизор Samsung 55", "salePriceU": 199990, "brand": "Samsung"},
            {"id": 1002, "name": "Телевизор LG 43", "salePriceU": 149990, "brand": "LG"},
        ]
    }
}


def _wb_handler(items_by_page: dict[int, list[dict]]):
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        return httpx.Response(200, json={"data": {"products": items_by_page.get(page, [])}})

    return handler


def test_wb_search_parses_and_paginates() -> None:
    extra = [{"id": 1003, "name": "Телевизор Xiaomi 50", "salePriceU": 129990, "brand": "Xiaomi"}]
    handler = _wb_handler({1: WB_JSON["data"]["products"], 2: extra})
    parser = WbParser(fetcher=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    products = asyncio.run(parser.search("телевизор", "belarus", limit_pages=2))
    assert len(products) == 3
    first = products[0]
    assert first.title == "Телевизор Samsung 55"
    assert first.price == 1999.9
    assert first.marketplace == "wb"
    assert first.url == "https://www.wildberries.ru/catalog/1001/detail.aspx"
    assert parser._truncated is True


def test_wb_search_stops_on_empty_page() -> None:
    handler = _wb_handler({1: WB_JSON["data"]["products"], 2: []})
    parser = WbParser(fetcher=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    products = asyncio.run(parser.search("телевизор", "belarus", limit_pages=3))
    assert len(products) == 2


OZON_JSON = {
    "widgetStates": {
        "searchPageResult": json.dumps(
            {
                "items": [
                    {
                        "title": "Телевизор Samsung QLED 55",
                        "skuId": 5550001,
                        "price": {"price": "2599.00", "cardPrice": "2499.00"},
                    },
                    {"title": "Телевизор LG 55", "skuId": 5550002, "price": "1999.00"},
                ]
            }
        )
    }
}


def _ozon_handler(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=OZON_JSON)


def _empty_ozon_handler(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"widgetStates": {}})


def test_ozon_search_extracts_products() -> None:
    parser = OzonParser(fetcher=httpx.AsyncClient(transport=httpx.MockTransport(_ozon_handler)))
    products = asyncio.run(parser.search("телевизор", "belarus"))
    assert len(products) == 2
    assert products[0].title == "Телевизор Samsung QLED 55"
    assert products[0].price == 2599.0
    assert products[0].url == "https://www.ozon.ru/product/5550001"
    assert products[0].marketplace == "ozon"


def test_ozon_search_returns_empty_on_missing_data() -> None:
    parser = OzonParser(
        fetcher=httpx.AsyncClient(transport=httpx.MockTransport(_empty_ozon_handler))
    )
    products = asyncio.run(parser.search("телевизор", "belarus"))
    assert products == []


def test_registry_lists_and_resolves_all_parsers() -> None:
    assert set(PARSERS) == {"kufar", "onliner", "ozon", "wb"}
    for marketplace_id in PARSERS:
        assert get_parser(marketplace_id) is not None
    assert get_parser("unknown") is None
    ids = {entry["marketplace_id"] for entry in list_parsers()}
    assert ids == set(PARSERS)


KUFAR_FILTERS_HTML = """
<html><body><script id="__NEXT_DATA__" type="application/json">
{"props":{"initialState":{"filters":{"currentFilters":[
  {"url_name":"prn","labels":{"name":{"ru":"Категория"}},
   "values":[{"labels":{"ru":"Планшеты"}},{"labels":{"ru":"Смартфоны"}}]},
  {"url_name":"bt","labels":{"name":{"ru":"Бренд"}},
   "values":[{"labels":{"ru":"Apple"}},{"labels":{"ru":"Samsung"}}]}
]}}}}
</script></body></html>
"""


def test_kufar_fetch_filters() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, text=KUFAR_FILTERS_HTML))
    parser = KufarParser(client=httpx.AsyncClient(transport=transport))
    filters = asyncio.run(parser.fetch_filters("планшет"))
    assert len(filters) == 2
    assert filters[0]["label"] == "Категория"
    assert "Планшеты" in filters[0]["options"]
    assert filters[1]["key"] == "bt"


def test_kufar_search_caps_items() -> None:
    many = [
        {
            "subject": f"Товар {index}",
            "ad_link": f"https://www.kufar.by/item/{index}",
            "price_byn": 10000 + index,
            "ad_parameters": [],
        }
        for index in range(3, 500)
    ]
    handler = _kufar_handler(KUFAR_HTML, {2: many[:2], 3: many[2:]})
    parser = KufarParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    parser.max_items = 3
    products = asyncio.run(parser.search("монитор", "belarus", limit_pages=3))
    assert len(products) == 4
    assert parser._truncated is True


def test_wb_falls_back_to_browser(monkeypatch) -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, text="not json"))
    parser = WbParser(fetcher=httpx.AsyncClient(transport=transport))

    async def fake_browser(query, region, products, seen) -> None:
        products.append(
            Product(
                title="Browser TV Samsung",
                price=99.0,
                old_price=None,
                currency="BYN",
                url="https://www.wildberries.ru/catalog/777/detail.aspx",
                marketplace="wb",
                region=region,
            )
        )

    monkeypatch.setattr(parser, "_browser_search", fake_browser)
    products = asyncio.run(parser.search("телевизор", "belarus"))
    assert len(products) == 1
    assert "Samsung" in products[0].title


def test_wb_raises_blocked_on_403() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(403))
    parser = WbParser(fetcher=httpx.AsyncClient(transport=transport))
    with pytest.raises(MarketplaceBlockedError):
        asyncio.run(parser.search("телевизор", "belarus"))


def test_ozon_falls_back_to_browser(monkeypatch) -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, text="not json"))
    parser = OzonParser(fetcher=httpx.AsyncClient(transport=transport))

    async def fake_browser_data(query: str) -> object:
        return OZON_JSON

    monkeypatch.setattr(parser, "_browser_search_data", fake_browser_data)
    products = asyncio.run(parser.search("телевизор", "belarus"))
    assert len(products) == 2
    assert products[0].marketplace == "ozon"


def test_ozon_raises_blocked_on_403() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(403))
    parser = OzonParser(fetcher=httpx.AsyncClient(transport=transport))
    with pytest.raises(MarketplaceBlockedError):
        asyncio.run(parser.search("телевизор", "belarus"))


def test_onliner_search_caps_items() -> None:
    handler = _onliner_handler({1: ONLINER_ITEMS, 2: ONLINER_ITEMS[:1], 3: ONLINER_ITEMS})
    parser = OnlinerParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    parser.max_items = 2
    products = asyncio.run(parser.search("монитор", "belarus", limit_pages=3))
    assert len(products) == 2
    assert parser._truncated is True
