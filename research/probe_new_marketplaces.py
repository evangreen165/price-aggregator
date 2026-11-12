"""Probe 21vek product dict + Deal.by embedded JSON."""

from __future__ import annotations

import json
import re
import sys

import httpx
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HEADERS = {
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
    v21 = client.get("https://www.21vek.by/search/", params={"q": "планшет"})
    deal = client.get("https://deal.by/search", params={"q": "планшет"})

initial = json.loads(json.loads(BeautifulSoup(v21.text, "html.parser").find("script", id="__NEXT_DATA__").string)["props"]["pageProps"]["initialState"])
products = initial["searchResult"].get("products", [])
print("21vek products:", len(products))
if products:
    print("21vek product keys:", list(products[0].keys())[:20])
    print("21vek sample:", json.dumps({k: products[0].get(k) for k in ("name", "price", "link", "vendor", "rating")}, ensure_ascii=False)[:300])
print("21vek paginationMeta:", json.dumps(initial["searchResult"].get("paginationMeta"), ensure_ascii=False)[:200])

blobs = re.findall(r'<script[^>]*>(.*?)</script>', deal.text, re.S)
for blob in blobs:
    if blob.startswith("{") and len(blob) > 2000:
        try:
            data = json.loads(blob)
        except ValueError:
            continue
        print("dealby script json keys:", list(data.keys())[:15] if isinstance(data, dict) else type(data).__name__)
        break
else:
    print("dealby: no big json script; checking __NEXT_DATA__")
    node = BeautifulSoup(deal.text, "html.parser").find("script", id="__NEXT_DATA__")
    print("dealby __NEXT_DATA__:", node is not None)
    if node and node.string:
        text = node.string
        for marker in ("products", "item", "search"):
            print("  marker", marker, ":", marker in text)
