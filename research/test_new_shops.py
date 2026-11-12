"""Research: 5element.by search variants + category page structure."""

from __future__ import annotations

import re
import sys

import httpx
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

URLS = [
    "https://5element.by/search/?q=телевизор",
    "https://5element.by/search?text=телевизор",
    "https://5element.by/search/?query=телевизор",
    "https://5element.by/catalog/1403-televizory",
]

with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=25) as client:
    for url in URLS:
        response = client.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select("a[href*='/product/']")
        print(f"{url} -> {response.status_code} len={len(response.text)} product_links={len(items)}")
        if items:
            for a in items[:3]:
                print("   ", (a.get("title") or a.get_text(" ", strip=True))[:70], "|", a.get("href")[:80])
            # price near product link
            node = items[0].find_parent("div", class_=re.compile("product|item|card")) or items[0]
            text = node.get_text(" ", strip=True)
            m = re.search(r"([\d\s]+)[\.,]?\d*\s*(?:р\.|руб|BYN|₽)", text)
            print("   price:", m.group(0) if m else None)
            break
