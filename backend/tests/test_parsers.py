import asyncio

import httpx

from app.parsers import PARSERS, get_parser, list_parsers
from app.parsers.kufar import KufarParser
from app.parsers.onliner import OnlinerParser
from app.parsers.stubs import OzonParser, WbParser

KUFAR_HTML = """
<html><body><script id="__NEXT_DATA__" type="application/json">
{"props":{"initialState":{"listing":{"ads":[
  {"subject":"Монитор 27 IPS", "ad_link":"https://www.kufar.by/item/1",
   "price_byn":41999, "currency":"BYR", "ad_parameters":[{"p":"region","vl":"Минск"}]},
  {"subject":"Монитор 24", "ad_link":"https://www.kufar.by/item/2",
   "price_byn":24900, "currency":"BYR", "ad_parameters":[]}
]}}}}
</script></body></html>
"""

ONLINER_JSON = {
    "products": [
        {
            "full_name": "ASUS ROG Swift OLED PG34WCDN",
            "html_url": "https://catalog.onliner.by/display/asus/pg34wcdn",
            "prices": {"price_min": {"amount": "6642.68", "currency": "BYN"}},
        }
    ]
}


def test_kufar_extract() -> None:
    parser = KufarParser()
    products = parser._extract(KUFAR_HTML, "belarus")
    assert len(products) == 2
    first = products[0]
    assert first.title == "Монитор 27 IPS"
    assert first.price == 419.99
    assert first.currency == "BYN"
    assert first.marketplace == "kufar"
    assert first.region == "Минск"
    assert products[1].region == "belarus"


def test_kufar_search_uses_mocked_http() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, text=KUFAR_HTML))
    parser = KufarParser(client=httpx.AsyncClient(transport=transport))
    products = asyncio.run(parser.search("монитор", "belarus"))
    assert len(products) == 2


def test_onliner_extract() -> None:
    parser = OnlinerParser()
    products = parser._extract(ONLINER_JSON, "belarus")
    assert len(products) == 1
    product = products[0]
    assert product.title == "ASUS ROG Swift OLED PG34WCDN"
    assert product.price == 6642.68
    assert product.marketplace == "onliner"


def test_onliner_search_uses_mocked_http() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=ONLINER_JSON))
    parser = OnlinerParser(client=httpx.AsyncClient(transport=transport))
    products = asyncio.run(parser.search("монитор", "belarus"))
    assert len(products) == 1


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
