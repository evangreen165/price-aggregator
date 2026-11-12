"""Research: OZ.by search product link/price structure."""

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

with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=25) as client:
    text = client.get("https://oz.by/search/?q=телевизор").text
soup = BeautifulSoup(text, "html.parser")

# find links whose href looks like a product page
candidates = {}
for a in soup.select("a[href]"):
    href = a.get("href", "")
    title = a.get("title") or a.get_text(" ", strip=True)
    if not title:
        continue
    for marker in ("/products/", "/product/", ".html", "/more/"):
        if marker in href:
            candidates.setdefault(marker, []).append((title[:50], href[:80]))
for marker, items in candidates.items():
    print(f"marker {marker}: {len(items)}")
    for item in items[:2]:
        print("   ", item)

# price patterns near product titles
blocks = soup.select("a[href]")
prices = re.findall(r"([\d\s]+[\.,]?\d*)\s*(?:р\.|руб|BYN)", soup.get_text(" ", strip=True))
print("price snippets:", prices[:6])
print("total price regex hits:", len(prices))
