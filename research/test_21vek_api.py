"""Research: 21vek with ?search= param + Deal.by XHR + AliExpress stealth."""

from __future__ import annotations

import json
import sys

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def capture_21vek(search_param: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="msedge")
        page = browser.new_page()
        captured: list[str] = []

        def on_response(response) -> None:
            url = response.url
            if "search-composer" in url or "products" in url:
                try:
                    captured.append(f"{response.request.method} {url}\n   {response.text()[:200]}")
                except Exception:
                    pass

        page.on("response", on_response)
        page.goto(f"https://www.21vek.by/search/?{search_param}", timeout=90000, wait_until="domcontentloaded")
        page.wait_for_timeout(9000)
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(4000)
        print(f"21vek {search_param}: captured {len(captured)}")
        for item in captured[:6]:
            print("  ", item.replace("\n", "\n   "))
        browser.close()


def capture_dealby() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="msedge")
        page = browser.new_page()
        captured: list[str] = []

        def on_response(response) -> None:
            url = response.url
            if any(m in url for m in ("graphql", "/api/", "my.deal", "search")):
                try:
                    body = response.text()[:180]
                except Exception:
                    body = ""
                captured.append(f"{response.request.method} {url}\n   {body}")

        page.on("response", on_response)
        page.goto("https://deal.by/search/?q=телевизор", timeout=90000, wait_until="domcontentloaded")
        page.wait_for_timeout(9000)
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(4000)
        print(f"dealby captured {len(captured)}")
        for item in captured[:10]:
            print("  ", item.replace("\n", "\n   ")[:200])
        browser.close()


def probe_aliexpress() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="msedge")
        page = browser.new_page()
        Stealth().use_sync(page)
        page.goto("https://aliexpress.ru/", timeout=90000, wait_until="domcontentloaded")
        page.wait_for_timeout(12000)
        print("aliexpress.ru title:", page.title()[:60])
        body = page.evaluate("() => document.body.innerText.slice(0, 200)")
        print("  body:", body.replace("\n", " | ")[:150])
        print("  captcha marker:", "captcha" in body.lower() or "проверка" in body.lower())
        browser.close()


if __name__ == "__main__":
    capture_21vek("search=телевизор")
    capture_dealby()
    probe_aliexpress()
