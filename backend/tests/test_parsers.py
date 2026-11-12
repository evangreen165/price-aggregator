import asyncio

import httpx

from app.parsers import PARSERS, get_parser, list_parsers
from app.parsers.kufar import KufarParser
from app.parsers.onliner import OnlinerParser
from app.parsers.stubs import OzonParser, WbParser

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
    {"num":2,"token":"T2"},
    {"num":3,"token":"T3"}
  ]
}}}}
</script></body></html>
"""

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


def _kufar_handler(html: str, extra_pages: dict[str, list[dict]]):
    def handler(request: httpx.Request) -> httpx.Response:
        if "search-api" in str(request.url):
            cursor = request.url.params.get("cursor")
            ads = extra_pages.get(cursor, [])
            return httpx.Response(200, json={"ads": ads})
        return httpx.Response(200, text=html)

    return handler


def test_kufar_search_collects_pages_and_dedupes() -> None:
    ad_c = {
        "subject": "Монитор 32 OLED",
        "ad_link": "https://www.kufar.by/item/3",
        "price_byn": 89900,
        "ad_parameters": [],
    }
    handler = _kufar_handler(KUFAR_HTML, {"T2": [ad_c, ad_c], "T3": []})
    parser = KufarParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    products = asyncio.run(parser.search("монитор", "belarus", limit_pages=3))
    assert len(products) == 3
    assert products[2].title == "Монитор 32 OLED"
    assert products[2].price == 899.0


def test_kufar_search_stops_when_no_new_items() -> None:
    handler = _kufar_handler(KUFAR_HTML, {"T2": [], "T3": []})
    parser = KufarParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    products = asyncio.run(parser.search("монитор", "belarus", limit_pages=3))
    assert len(products) == 2


def test_kufar_search_respects_limit_pages() -> None:
    handler = _kufar_handler(KUFAR_HTML, {})
    parser = KufarParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    products = asyncio.run(parser.search("монитор", "belarus", limit_pages=1))
    assert len(products) == 2


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


def test_onliner_search_stops_on_empty_page() -> None:
    handler = _onliner_handler({1: ONLINER_ITEMS, 2: []})
    parser = OnlinerParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    products = asyncio.run(parser.search("монитор", "belarus", limit_pages=3))
    assert len(products) == 2


def test_stub_parsers_return_empty() -> None:
    assert asyncio.run(OzonParser().search("монитор", "belarus")) == []
    assert asyncio.run(WbParser().search("монитор", "belarus")) == []


def test_registry_lists_and_resolves_all_parsers() -> None:
    assert set(PARSERS) == {"kufar", "onliner", "ozon", "wb"}
    for marketplace_id in PARSERS:
        assert get_parser(marketplace_id) is not None
    assert get_parser("unknown") is None
    ids = {entry["marketplace_id"] for entry in list_parsers()}
    assert ids == set(PARSERS)
