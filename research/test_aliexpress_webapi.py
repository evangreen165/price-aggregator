"""Research: AliExpress aer-webapi/v2/recommend snippetsV2 structure."""

from __future__ import annotations

import json
import sys

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

QUERY = "телевизор"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="msedge")
    page = browser.new_page()
    Stealth().use_sync(page)
    payload: dict | None = None

    def on_response(response) -> None:
        global payload
        if "aer-webapi" in response.url and "recommend" in response.url:
            try:
                payload = response.json()
            except Exception:
                pass

    page.on("response", on_response)
    page.goto(f"https://aliexpress.ru/wholesale?SearchText={QUERY}", timeout=90000, wait_until="domcontentloaded")
    page.wait_for_timeout(15000)
    page.mouse.wheel(0, 3000)
    page.wait_for_timeout(3000)

    if not payload:
        print("no aer-webapi recommend payload")
        browser.close()
        raise SystemExit(1)
    data = payload.get("data") or {}
    snippets = data.get("snippetsV2") or []
    print("snippetsV2:", len(snippets))
    if snippets:
        first = snippets[0]
        print("first snippet keys:", list(first.keys())[:20])
        print("sample:", json.dumps(first, ensure_ascii=False)[:1500])
    browser.close()
