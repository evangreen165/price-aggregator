"""Research: 21vek search-composer POST probe."""

from __future__ import annotations

import json
import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}

bodies = [
    {"query": "телевизор", "page": 2},
    {"term": "телевизор", "page": 2},
    {"query": "телевизор", "page": 2, "mode": "desktop"},
]

with httpx.Client(headers=HEADERS, timeout=25) as client:
    for path in ("search", "search/products"):
        for body in bodies:
            try:
                r = client.post(f"https://gate.21vek.by/search-composer/api/v1/{path}", json=body)
                print(path, list(body.keys()), "->", r.status_code, len(r.text))
                if r.status_code == 200 and r.text.startswith("{"):
                    data = r.json()
                    print("  keys:", list(data.keys())[:8])
                    break
            except Exception as exc:  # noqa: BLE001
                print(path, "err", type(exc).__name__)
