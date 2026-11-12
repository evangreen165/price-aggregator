import asyncio
import base64
import json

import httpx

from app.parsers import PARSERS, get_parser, list_parsers
from app.parsers.aliexpress import AliExpressParser
from app.parsers.dealby import DealByParser
from app.parsers.kufar import KufarParser
from app.parsers.onliner import OnlinerParser
from app.parsers.vek21 import TwentyOneVekParser


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
    assert products[0].title == "Монитор 27 IPS"
    assert products[0].price == 419.99
    assert products[0].region == "Минск"


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
    products = asyncio.run(parser.search("монитор", "belarus", limit_pages=2))
    assert len(products) == 3


def test_kufar_search_continues_from_page_start() -> None:
    ad_d = {
        "subject": "Монитор 34",
        "ad_link": "https://www.kufar.by/item/4",
        "price_byn": 70000,
        "ad_parameters": [],
    }
    handler = _kufar_handler(KUFAR_HTML, {3: [ad_d]})
    parser = KufarParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    products = asyncio.run(parser.search("монитор", "belarus", limit_pages=1, page_start=3))
    assert [product.title for product in products] == ["Монитор 34"]


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
    assert filters[0]["label"] == "Категория"
    assert "Планшеты" in filters[0]["options"]


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
    products = asyncio.run(parser.search("монитор", "belarus", limit_pages=2))
    assert len(products) == 4
    assert parser._truncated is True


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


def test_onliner_search_continues_from_page_start() -> None:
    extra = [
        {
            "full_name": "Dell 27",
            "html_url": "https://catalog.onliner.by/display/dell/27",
            "prices": {"price_min": {"amount": "500.0", "currency": "BYN"}},
        }
    ]
    handler = _onliner_handler({5: extra})
    parser = OnlinerParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    products = asyncio.run(parser.search("монитор", "belarus", limit_pages=1, page_start=5))
    assert len(products) == 1


def test_onliner_search_applies_filters() -> None:
    handler = _onliner_handler({1: ONLINER_ITEMS})
    parser = OnlinerParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    products = asyncio.run(
        parser.search("монитор", "belarus", limit_pages=1, filters={"brand": ["Samsung"]})
    )
    assert len(products) == 1
    assert "Samsung" in products[0].title


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


def test_onliner_search_caps_items() -> None:
    handler = _onliner_handler({1: ONLINER_ITEMS, 2: ONLINER_ITEMS[:1], 3: ONLINER_ITEMS})
    parser = OnlinerParser(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    parser.max_items = 2
    products = asyncio.run(parser.search("монитор", "belarus", limit_pages=3))
    assert len(products) == 2
    assert parser._truncated is True


ALIEXPRESS_HTML = """
<script>
window.runParams = {"data": {"subject": "Планшет Xiaomi Pad", "salePrice": "199.99",
  "productId": "1005001", "productDetailUrl": "https://www.aliexpress.com/item/1005001.html"}};
</script>
"""


def test_aliexpress_extract_and_add() -> None:
    parser = AliExpressParser()
    items = parser._extract(ALIEXPRESS_HTML)
    assert len(items) == 1
    products: list = []
    parser._add_products(products, set(), items, "belarus")
    assert products[0].title == "Планшет Xiaomi Pad"
    assert products[0].price == 199.99
    assert products[0].marketplace == "aliexpress"


def test_aliexpress_search_collects(monkeypatch) -> None:
    parser = AliExpressParser()

    async def fake_fetch_page(query: str, page: int) -> object:
        return [
            {"title": f"Планшет {page}", "price": "100", "productId": str(page), "url": None}
        ]

    monkeypatch.setattr(parser, "_fetch_page", fake_fetch_page)
    products = asyncio.run(parser.search("планшет", "belarus", limit_pages=2))
    assert len(products) == 2


_VEK21_STATE = {
    "searchResult": {
        "products": {
            "1": {
                "name": "Планшет Apple iPad 10",
                "link": "/products/1",
                "price": {"price": "1200.00"},
            }
        },
        "vendors": ["Apple", "Samsung", "Xiaomi"],
    }
}

VEK21_HTML = """
<html><body><script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"initialState":%s}}}
</script></body></html>
""" % json.dumps(json.dumps(_VEK21_STATE, ensure_ascii=False))


def test_vek21_extract_and_add() -> None:
    parser = TwentyOneVekParser()
    items = parser._extract(VEK21_HTML)
    assert len(items) == 1
    products: list = []
    parser._add_products(products, set(), items, "belarus")
    assert products[0].title == "Планшет Apple iPad 10"
    assert products[0].price == 1200.0
    assert products[0].url == "https://www.21vek.by/products/1"


def test_vek21_search_and_filters() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, text=VEK21_HTML))
    parser = TwentyOneVekParser(client=httpx.AsyncClient(transport=transport))
    products = asyncio.run(parser.search("планшет", "belarus", limit_pages=1))
    assert len(products) == 1
    filters = asyncio.run(parser.fetch_filters("планшет"))
    assert filters[0]["key"] == "brand"
    assert "Apple" in filters[0]["options"]


DEALBY_HTML = """
<html><body>
<div class="search-item">
  <a href="/item/12345" title="Планшет Lenovo Tab">Планшет Lenovo Tab</a>
  <span>599.00 р.</span>
</div>
<div class="search-item">
  <a href="/goods/999" title="Планшет Prestigio">Планшет Prestigio</a>
  <span>349.00 р.</span>
</div>
</body></html>
"""


def test_dealby_extract_and_add() -> None:
    parser = DealByParser()
    items = parser._extract(DEALBY_HTML)
    assert len(items) == 2
    products: list = []
    parser._add_products(products, set(), items, "belarus")
    assert products[0].title == "Планшет Lenovo Tab"
    assert products[0].price == 599.0
    assert products[0].url == "https://deal.by/item/12345"


def test_dealby_search() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, text=DEALBY_HTML))
    parser = DealByParser(client=httpx.AsyncClient(transport=transport))
    products = asyncio.run(parser.search("планшет", "belarus", limit_pages=1))
    assert len(products) == 2


def test_registry_lists_and_resolves_all_parsers() -> None:
    assert set(PARSERS) == {"kufar", "onliner", "aliexpress", "21vek", "dealby"}
    for marketplace_id in PARSERS:
        assert get_parser(marketplace_id) is not None
    assert get_parser("ozon") is None
    assert get_parser("wb") is None
    ids = {entry["marketplace_id"] for entry in list_parsers()}
    assert ids == set(PARSERS)
