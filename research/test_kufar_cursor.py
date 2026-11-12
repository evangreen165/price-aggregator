"""Isolate: kufar cursor continuation for 'монитор 27 2K'."""

from __future__ import annotations

import base64
import json
import sys
import time

import httpx
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "ru-RU,ru;q=0.9"}

with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
    html = client.get("https://www.kufar.by/l", params={"query": "монитор 27 2K"}).text
    listing = json.loads(BeautifulSoup(html, "html.parser").find("script", id="__NEXT_DATA__").string)["props"]["initialState"]["listing"]
    token = next(e for e in listing["pagination"] if e.get("token"))
    pit = json.loads(base64.b64decode(token["token"]))["pit"]
    print("pit:", pit)
    for page in (2, 3, 4, 5):
        cur = base64.b64encode(json.dumps({"t": "abs", "f": True, "p": page, "pit": pit}, separators=(",", ":")).encode()).decode()
        time.sleep(1.5)
        response = client.get(
            "https://api.kufar.by/search-api/v2/search/rendered",
            params={"query": "монитор 27 2K", "size": 50, "lang": "ru", "cursor": cur},
        )
        ads = response.json().get("ads", []) if response.status_code == 200 else []
        print(f"page {page}: status={response.status_code} ads={len(ads)}")
