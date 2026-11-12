"""Research: Deal.by public API probes (my.deal.by/api/v1) + XHR capture."""

from __future__ import annotations

import sys

import httpx
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "ru"}

CANDIDATES = [
    ("products/search", {"q": "телевизор"}),
    ("search", {"q": "телевизор"}),
    ("products", {"search": "телевизор"}),
    ("catalog/search", {"q": "телевизор"}),
    ("search/products", {"q": "телевизор"}),
]


def probe_api() -> None:
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=25) as client:
        for path, params in CANDIDATES:
            url = f"https://my.deal.by/api/v1/{path}"
            try:
                response = client.get(url, params=params)
                print(f"dealby api {path} {params} -> {response.status_code} len={len(response.text)}")
                if response.status_code == 200:
                    try:
                        print("   body:", response.json())
                    except ValueError:
                        print("   body:", response.text[:150])
            except Exception as exc:  # noqa: BLE001
                print(f"dealby api {path} -> error {type(exc).__name__}")


def capture_xhr() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="msedge")
        page = browser.new_page()
        captured: list[str] = []

        def on_response(response) -> None:
            url = response.url
            if any(m in url for m in ("/api/", "graphql", "search")):
                try:
                    body = response.text()[:160]
                except Exception:
                    body = ""
                captured.append(f"{response.request.method} {url}\n   {body}")

        page.on("response", on_response)
        page.goto("https://deal.by/search/?q=телевизор", timeout=90000, wait_until="domcontentloaded")
        page.wait_for_timeout(12000)
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(4000)
        print(f"dealby captured {len(captured)}")
        for item in captured[:12]:
            print("  ", item[:220])
        browser.close()


if __name__ == "__main__":
    probe_api()
    capture_xhr()
