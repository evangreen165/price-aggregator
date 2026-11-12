from fastapi.testclient import TestClient

from app.main import app
from app.plugins import PluginManager, get_manager


def test_plugins_endpoint_lists_example() -> None:
    with TestClient(app) as client:
        response = client.get("/api/plugins")
    assert response.status_code == 200
    ids = [plugin["marketplace_id"] for plugin in response.json()]
    assert "example" in ids


def test_reload_endpoint_keeps_example() -> None:
    with TestClient(app) as client:
        response = client.post("/api/plugins/reload")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "example" in [plugin["marketplace_id"] for plugin in body["plugins"]]


def test_plugin_manager_registers_example_parser() -> None:
    manager = PluginManager()
    manager.load_all()
    assert "example" in manager.registry
    assert manager.registry["example"].__name__ == "ExampleParser"


def test_global_manager_has_example_after_load() -> None:
    manager = get_manager()
    manager.load_all()
    assert "example" in manager.registry
