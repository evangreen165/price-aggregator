"""Plugin discovery and loading built on pluggy."""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path

import pluggy

from app.core.config import PLUGINS_DIR

logger = logging.getLogger(__name__)

PROJECT_NAME = "price_aggregator"
MODULE_PREFIX = "pa_plugin_"

hookspec = pluggy.HookspecMarker(PROJECT_NAME)
hookimpl = pluggy.HookimplMarker(PROJECT_NAME)


class ParserHookSpec:
    """Hook specifications implemented by parser plugins."""

    @hookspec
    def register_parser(self) -> tuple[str, type] | None:
        """Register a parser.

        Implementations take no arguments and return a ``(marketplace_id, parser_class)``
        tuple, or ``None`` to skip registration. The host collects all returned tuples
        into its registry keyed by ``marketplace_id``.
        """


class PluginManager:
    """Loads parser plugins from the plugins directory into a registry."""

    def __init__(self, plugins_dir: Path | None = None) -> None:
        self.plugins_dir = Path(plugins_dir) if plugins_dir is not None else PLUGINS_DIR
        self.registry: dict[str, type] = {}
        self._sources: dict[str, str] = {}
        self._counter = 0
        self.pm = pluggy.PluginManager(PROJECT_NAME)
        self.pm.add_hookspecs(ParserHookSpec)

    def load_all(self) -> dict[str, type]:
        """Import every plugin module in the plugins directory and collect registrations."""
        if not self.plugins_dir.is_dir():
            logger.warning("Plugins directory not found: %s", self.plugins_dir)
            return self.registry

        importlib.invalidate_caches()
        for path in sorted(self.plugins_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            self._load_file(path)

        for result in self.pm.hook.register_parser():
            if not result:
                continue
            marketplace_id, parser_class = result
            self.registry[marketplace_id] = parser_class

        return self.registry

    def _load_file(self, path: Path) -> None:
        self._counter += 1
        module_name = f"{MODULE_PREFIX}{path.stem}_{self._counter}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot create module spec for {path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        except Exception:  # noqa: BLE001 - a broken plugin must not kill the app
            logger.exception("Failed to load plugin module %s", path)
            sys.modules.pop(module_name, None)
            return

        self._sources[module_name] = path.name
        try:
            self.pm.register(module, name=module_name)
        except ValueError:
            logger.warning("Plugin module already registered: %s", path)

    def reload(self) -> "PluginManager":
        """Drop loaded plugin modules and build a fresh manager with reloaded plugins."""
        for name in [n for n in sys.modules if n.startswith(MODULE_PREFIX)]:
            sys.modules.pop(name, None)
        importlib.invalidate_caches()
        fresh = PluginManager(self.plugins_dir)
        fresh.load_all()
        self.registry = fresh.registry
        self._sources = fresh._sources
        self._counter = fresh._counter
        self.pm = fresh.pm
        return self

    def list_plugins(self) -> list[dict]:
        """Return serialisable metadata about every registered parser."""
        plugins: list[dict] = []
        for marketplace_id, parser_class in sorted(self.registry.items()):
            plugins.append(
                {
                    "marketplace_id": marketplace_id,
                    "name": getattr(parser_class, "name", marketplace_id),
                    "version": getattr(parser_class, "version", "0.0.0"),
                    "file": self._source_for(parser_class),
                    "parser_class": getattr(parser_class, "__name__", str(parser_class)),
                }
            )
        return plugins

    def _source_for(self, parser_class: type) -> str:
        module = sys.modules.get(getattr(parser_class, "__module__", ""), None)
        if module is not None:
            path = getattr(module, "__file__", None)
            if path:
                return Path(path).name
        return ""


manager = PluginManager()


def get_manager() -> PluginManager:
    """Return the process-wide plugin manager."""
    return manager
