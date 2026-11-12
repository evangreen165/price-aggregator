"""Research: 21vek SSR product markup + AliExpress aer-webapi curl body."""

from __future__ import annotations

import json
import re
import sys

import httpx
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "ru-RU,ru;q=0.9"}


def vek21() -> None:
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        r = client.get("https://www.21vek.by/search/", params={"term": "телевизор"})
    text = r.text
    print("21vek ?term= len:", len(text))
    node = BeautifulSoup(text, "html.parser").find("script", id="__NEXT_DATA__")
    state = json.loads(json.loads(node.string)["props"]["pageProps"]["initialState"])
    products = state.get("searchResult", {}).get("products", {})
    print("  searchResult.products:", json.dumps(products, ensure_ascii=False)[:400])
    print("  has code 10050013 in html:", "10050013" in text)
    soup = BeautifulSoup(text, "html.parser")
    for sel in ("a[href*='/products/']", "[data-testid*='product']", "h2 a", "h3 a"):
        found = soup.select(sel)
        print(f"  selector {sel}: {len(found)}")
        for f in found[:3]:
            print("    ", f.get_text(" ", strip=True)[:60], "|", (f.get("href") or "")[:70])


def aliexpress() -> None:
    state = json.loads(open("research/aliexpress_state.json", encoding="utf-8").read())
    cookies = {c["name"]: c["value"] for c in state.get("cookies", [])}
    from curl_cffi import requests

    with requests.Session(impersonate="chrome") as session:
        for version in ("v1", "v2"):
            response = session.get(
                f"https://aliexpress.ru/aer-webapi/{version}/search",
                params={"SearchText": "телевизор", "page": 1, "size": 20},
                headers={"Accept-Language": "ru-RU,ru;q=0.9", "User-Agent": "Mozilla/5.0"},
                cookies=cookies,
                timeout=25,
            )
            body = response.text
            print(f"aer-webapi/{version}/search -> {response.status_code} len={len(body)}")
            print("   body[:200]:", body[:200].replace("\n", " "))
            try:
                data = response.json()
                top = data.get("data") or {}
                print("   keys:", list(top.keys())[:10])
                for key in ("productsFeed", "snippetsV2", "snippets", "products"):
                    value = top.get(key)
                    if isinstance(value, list) and value:
                        print(f"   {key}: {len(value)} items, first keys:", list(value[0].keys())[:12])
            except ValueError:
                pass


if __name__ == "__main__":
    vek21()
    aliexpress()
