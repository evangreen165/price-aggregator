"""Research: Kufar deep pagination + Onliner sort-based >1000 items."""

from __future__ import annotations

import base64
import json
import sys

import httpx
from bs4 import BeautifulSoup
from curl_cffi import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HEADERS = {
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

ENDPOINTS = [
    "https://api.kufar.by/search-api/v2/search/rendered",
    "https://api.kufar.by/search-api/v2/search/rendered-paginated",
]


def kufar_pagination() -> None:
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        html = client.get("https://www.kufar.by/l", params={"query": "телевизор"}).text
    listing = json.loads(BeautifulSoup(html, "html.parser").find("script", id="__NEXT_DATA__").string)["props"]["initialState"]["listing"]
    token = next((e for e in listing["pagination"] if e.get("token")), None)
    pit = json.loads(base64.b64decode(token["token"])).get("pit") if token else None
    print("kufar pit:", pit)

    for endpoint in ENDPOINTS:
        total = 0
        unique: set[str] = set()
        with requests.Session(impersonate="chrome") as session:
            for page in (4, 5, 6, 7, 8, 9, 10):
                cursor = base64.b64encode(json.dumps({"t": "abs", "f": True, "p": page, "pit": pit}, separators=(",", ":")).encode()).decode()
                response = session.get(
                    endpoint,
                    params={"query": "телевизор", "size": 50, "lang": "ru", "cursor": cursor},
                    headers=HEADERS,
                    timeout=25,
                )
                ads = response.json().get("ads", []) if response.status_code == 200 else []
                before = len(unique)
                for ad in ads:
                    url = ad.get("ad_link")
                    if url:
                        unique.add(url)
                total += len(ads)
                print(f"  {endpoint.rsplit('/', 1)[-1]} page={page} status={response.status_code} ads={len(ads)} new={len(unique) - before}")
        print(f"  TOTAL unique for {endpoint.rsplit('/', 1)[-1]}: {len(unique)}")


def onliner_sorts() -> None:
    sorts = ["relevance", "price_asc", "price_desc", "date"]
    unique: set[str] = set()
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        for sort in sorts:
            for page in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10):
                params = {"query": "телевизор", "group": "1", "limit": 100, "page": page}
                if sort != "relevance":
                    params["sort"] = sort
                data = client.get("https://catalog.onliner.by/sdapi/catalog.api/search/products", params=params).json()
                products = data.get("products", [])
                if not products:
                    break
                for product in products:
                    url = product.get("html_url")
                    if url:
                        unique.add(url)
        print(f"ONLINER total unique across sorts: {len(unique)}")


if __name__ == "__main__":
    kufar_pagination()
    onliner_sorts()
