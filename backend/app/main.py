"""FastAPI application and desktop (pywebview) entry point."""

from __future__ import annotations

import logging
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.core.config import (
    APP_NAME,
    FRONTEND_DIST,
    HOST,
    IS_FROZEN,
    LOG_FILE,
    PORT,
    USER_AGENT,
)
from app.parsers import get_parser
from app.parsers.base import MarketplaceBlockedError
from app.plugins import get_manager

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    # In --windowed builds sys.stdout/stderr are None, so only log to the file.
    if IS_FROZEN:
        handlers: list[logging.Handler] = [logging.FileHandler(LOG_FILE, encoding="utf-8")]
    else:
        handlers = [logging.StreamHandler()]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _configure_logging()
    get_manager().load_all()
    yield


app = FastAPI(title=APP_NAME, lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


_PROXY_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}
_PROXY_BLOCKED_HEADERS = {
    "content-length",
    "content-encoding",
    "transfer-encoding",
    "x-frame-options",
    "content-security-policy",
}


@app.get("/proxy")
async def proxy(url: str = "") -> Response:
    """Fetch a page server-side so external sites can be embedded in the app iframe."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return JSONResponse({"detail": "invalid url"}, status_code=400)
    async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
        upstream = await client.get(url, headers=_PROXY_HEADERS)
    headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in _PROXY_BLOCKED_HEADERS
    }
    return Response(content=upstream.content, status_code=upstream.status_code, headers=headers)


@app.get("/api/plugins")
def list_plugins() -> list[dict]:
    return get_manager().list_plugins()


@app.post("/api/plugins/reload")
def reload_plugins() -> dict:
    manager = get_manager().reload()
    return {"status": "ok", "plugins": manager.list_plugins()}


class SearchRequest(BaseModel):
    query: str
    marketplaces: list[str] = []
    region: str = "belarus"
    limit_pages: int = 10
    filters: dict[str, list[str]] = {}
    page: dict[str, int] = {}
    cursor: dict[str, str] = {}


@app.post("/api/search")
async def search(req: SearchRequest) -> dict:
    results: dict[str, list[dict]] = {}
    errors: dict[str, str] = {}
    meta: dict[str, dict] = {}
    next_page: dict[str, int | None] = {}
    next_cursor: dict[str, str | None] = {}
    for marketplace_id in req.marketplaces:
        parser = get_parser(marketplace_id)
        if parser is None:
            continue
        results[marketplace_id] = []
        meta[marketplace_id] = {"truncated": False}
        next_page[marketplace_id] = None
        next_cursor[marketplace_id] = None
        try:
            products = await parser.search(
                req.query,
                req.region,
                req.limit_pages,
                req.filters,
                req.page.get(marketplace_id, 1),
                req.cursor.get(marketplace_id),
            )
            results[marketplace_id] = [product.to_dict() for product in products]
            truncated = bool(getattr(parser, "_truncated", False))
            meta[marketplace_id] = {"truncated": truncated}
            if truncated:
                next_page[marketplace_id] = req.page.get(marketplace_id, 1) + req.limit_pages
                next_cursor[marketplace_id] = getattr(parser, "_next_cursor", None)
        except MarketplaceBlockedError:
            errors[marketplace_id] = "Заблокировано (403)"
        except Exception as exc:  # noqa: BLE001 - a failing marketplace must not break others
            logger.exception("Search failed for marketplace %s", marketplace_id)
            errors[marketplace_id] = str(exc)
    return {
        "results": results,
        "errors": errors,
        "meta": meta,
        "next_page": next_page,
        "next_cursor": next_cursor,
    }


if FRONTEND_DIST.is_dir():
    _assets = FRONTEND_DIST / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        if full_path:
            candidate = FRONTEND_DIST / full_path
            try:
                resolved = candidate.resolve()
                if resolved.is_file() and resolved.is_relative_to(FRONTEND_DIST.resolve()):
                    return FileResponse(resolved)
            except OSError:
                pass
        return FileResponse(FRONTEND_DIST / "index.html")


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return True
    return False


def _wait_for_health(url: str, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.2)
    return False


_BACK_BUTTON_JS = """
(function () {
  if (document.getElementById('pa-back-btn')) return;
  var btn = document.createElement('button');
  btn.id = 'pa-back-btn';
  btn.textContent = '\\u2190 \\u041d\\u0430\\u0437\\u0430\\u0434';
  btn.style.cssText =
    'position:fixed;top:12px;left:12px;z-index:2147483647;padding:8px 14px;' +
    'font-size:14px;font-family:Segoe UI,Arial,sans-serif;background:#4c8dff;' +
    'color:#fff;border:none;border-radius:8px;cursor:pointer;' +
    'box-shadow:0 2px 8px rgba(0,0,0,.35)';
  btn.onclick = function () { history.back(); };
  document.body.appendChild(btn);
})();
"""


class DesktopApi:
    """JavaScript bridge exposed to the webview UI."""

    def __init__(self) -> None:
        self.window = None

    def open_link(self, url: str, mode: str) -> str:
        """Open a product link according to the user-selected mode."""
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return "invalid url"
        try:
            if mode == "system":
                webbrowser.open(url)
                return "opened in system browser"
            if mode == "new_window":
                import webview

                webview.create_window("Товар", url, width=1100, height=750)
                return "opened in new window"
            if self.window is not None:
                self.window.load_url(url)
                self.window.events.loaded += lambda: self.window.evaluate_js(
                    _BACK_BUTTON_JS
                )
                return "opened in current window"
        except Exception as exc:  # noqa: BLE001 - fall back to the system browser
            logger.exception("open_link failed for %s", url)
            webbrowser.open(url)
            return f"fallback to system browser: {exc}"
        return "no window available"


def run_desktop() -> None:
    """Start uvicorn in a background thread, then open the native window."""
    _configure_logging()
    # pywebview's accessibility event formatting recurses deeply in some
    # WebView2/Windows environments; give it room so it completes instead of
    # raising RecursionError in the GUI thread.
    sys.setrecursionlimit(10000)
    logger.info("Starting desktop app (%s frozen=%s)...", APP_NAME, IS_FROZEN)

    if _port_in_use(HOST, PORT):
        logger.error("Port %s:%s is already in use; close the other instance.", HOST, PORT)
        return
    logger.info("Port %s:%s is free", HOST, PORT)

    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="info", log_config=None)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="uvicorn", daemon=True)
    thread.start()
    logger.info("Uvicorn thread started (daemon=True)")

    url = f"http://{HOST}:{PORT}"
    if not _wait_for_health(f"{url}/api/health"):
        logger.error("Backend did not become healthy at %s; aborting.", url)
        server.should_exit = True
        return
    logger.info("Backend is healthy at %s", url)

    import webview

    # Prevent the known WebView2 accessibility recursion that crashes pywebview
    # under load (maximum recursion depth exceeded in AccessibilityObject polling).
    os.environ.setdefault(
        "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "--disable-renderer-accessibility"
    )
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = False

    api = DesktopApi()
    window = webview.create_window(
        APP_NAME,
        url,
        width=1200,
        height=800,
        min_size=(900, 600),
        js_api=api,
    )
    api.window = window
    # Keep a reference for open_link() but prevent pywebview's JS-bridge from
    # recursively walking the Window -> native WebView2 control (its
    # accessibility tree recurses without bound and crashes the GUI thread).
    api.window._serializable = False
    logger.info("WebView window created, starting GUI loop")
    webview.start()
    logger.info("GUI loop exited")


if __name__ == "__main__":
    run_desktop()
