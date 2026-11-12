"""FastAPI application and desktop (pywebview) entry point."""

from __future__ import annotations

import logging
import socket
import threading
import time
import urllib.error
import urllib.request
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.core.config import APP_NAME, FRONTEND_DIST, HOST, IS_FROZEN, LOG_FILE, PORT
from app.parsers import get_parser
from app.parsers.categories import classify, filters_for_query
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


@app.get("/api/filters")
def filters(query: str = "") -> dict:
    return {"query": query, "category": classify(query), "filters": filters_for_query(query)}


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


@app.post("/api/search")
async def search(req: SearchRequest) -> dict:
    results: dict[str, list[dict]] = {}
    errors: dict[str, str] = {}
    for marketplace_id in req.marketplaces:
        parser = get_parser(marketplace_id)
        if parser is None:
            continue
        results[marketplace_id] = []
        try:
            products = await parser.search(req.query, req.region)
            results[marketplace_id] = [product.to_dict() for product in products]
        except Exception as exc:  # noqa: BLE001 - a failing marketplace must not break others
            logger.exception("Search failed for marketplace %s", marketplace_id)
            errors[marketplace_id] = str(exc)
    return {"results": results, "errors": errors}


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


def run_desktop() -> None:
    """Start uvicorn in a background thread, then open the native window."""
    _configure_logging()

    if _port_in_use(HOST, PORT):
        logger.error("Port %s:%s is already in use; close the other instance.", HOST, PORT)
        return

    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="info", log_config=None)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="uvicorn", daemon=True)
    thread.start()

    url = f"http://{HOST}:{PORT}"
    if not _wait_for_health(f"{url}/api/health"):
        logger.error("Backend did not become healthy at %s; aborting.", url)
        server.should_exit = True
        return

    import webview

    webview.create_window(APP_NAME, url, width=1200, height=800, min_size=(900, 600))
    webview.start()


if __name__ == "__main__":
    run_desktop()
