"""Research: find 21vek real pagination param."""

from __future__ import annotations

import json
import sys

import httpx
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "ru-RU,ru;q=0.9"}

BASE = {"term": "телевизор"}

VARIANTS = [
    {"page": 2},
    {"page": 2, "page_size": 60},
    {"offset": 60},
    {"from": 60},
    {"limit": 60},
    {"page": 2, "sort": "price_asc"},
    {"page": "2"},
]

with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
    baseline = None
    for variant in VARIANTS:
        params = {**BASE, **variant}
        r = client.get("https://www.21vek.by/search/", params=params)
        node = BeautifulSoup(r.text, "html.parser").find("script", id="__NEXT_DATA__")
        try:
            state = json.loads(json.loads(node.string)["props"]["pageProps"]["initialState"])
        except Exception:
            print(variant, "-> parse error")
            continue
        products = state.get("searchResult", {}).get("products", {}).get("all", [])
        meta = state.get("searchResult", {}).get("paginationMeta", {})
        first = products[0].get("name", "")[:40] if products else None
        if baseline is None:
            baseline = first
        print(f"{variant}: count={len(products)} first={first} metaPage={meta.get('currentPage')} different={first != baseline}")
