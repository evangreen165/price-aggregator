"""Research: Kufar currentFilters + Onliner facets API endpoints."""

from __future__ import annotations

import json
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


def kufar_filters() -> None:
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        html = client.get("https://www.kufar.by/l", params={"query": "телевизор"}).text
    state = json.loads(BeautifulSoup(html, "html.parser").find("script", id="__NEXT_DATA__").string)["props"]["initialState"]
    current = state.get("filters", {}).get("currentFilters", [])
    print("kufar currentFilters groups:", len(current))
    for entry in current[:8]:
        name = ((entry.get("labels") or {}).get("name") or {}).get("ru")
        values = [(v.get("labels") or {}).get("ru") for v in (entry.get("values") or [])]
        values = [v for v in values if v]
        print("  -", name, "| url_name:", entry.get("url_name"), "| options:", values[:6], "..." if len(values) > 6 else "")


def onliner_facets_api() -> None:
    candidates = [
        ("search/catalog", {"query": "планшет", "group": "1"}),
        ("filters", {"query": "планшет"}),
        ("search/filters", {"query": "планшет"}),
        ("search/products", {"query": "планшет", "group": "1", "facets": "1"}),
        ("search/products", {"query": "планшет", "group": "1", "search_type": "facet"}),
    ]
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        for path, params in candidates:
            url = f"https://catalog.onliner.by/sdapi/catalog.api/{path}"
            response = client.get(url, params=params)
            text = response.text
            has_facets = "facet" in text.lower() or "attribute" in text.lower()
            print(f"onliner {path} {params} -> status={response.status_code} facets_marker={has_facets} len={len(text)}")
            if response.status_code == 200:
                try:
                    data = response.json()
                    keys = list(data.keys())[:12] if isinstance(data, dict) else type(data).__name__
                    print("   keys:", keys)
                except ValueError:
                    print("   body:", text[:120])


if __name__ == "__main__":
    kufar_filters()
    onliner_facets_api()
