"""Research: locate Onliner /tv filter markup."""

from __future__ import annotations

import re

import httpx

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}

with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
    html = client.get("https://catalog.onliner.by/tv").text

for pattern, label in (
    (r"facet", "facet"),
    (r"filter", "filter"),
    (r"f\[", "f["),
    (r"f%5B", "f%5B"),
    (r"catalog-filter", "catalog-filter"),
):
    matches = re.findall(pattern, html)
    print(f"hits for {label!r}:", len(matches))

snippets = re.findall(r'.{30}(?:facet|filter).{60}', html)[:5]
for s in snippets:
    print("  snippet:", s[:110])

selects = re.findall(r'<select[^>]*>(.{0,120})', html)[:5]
print("selects:", len(selects))
for s in selects:
    print("  select:", s[:100])
