"""Проверка регистрации инструментов/ресурсов MCP-сервера (без SDK `mcp`).

Подменяет `mcp.server.MCPServer` заглушкой и проверяет, что `server.py` регистрирует
ровно 3 инструмента и 5 ресурсов с ожидаемыми именами/URI. Логику самих инструментов
проверяет tests/test_mcp.py; полный transport-тест требует `pip install "mcp[cli]"`.

Запуск (из корня пакета select-radial-fan):
    python tests/test_mcp_registration.py
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class _FakeMCPServer:
    def __init__(self, name):
        self.name = name
        self.tools = []
        self.resources = []

    def tool(self):
        def deco(fn):
            self.tools.append(fn.__name__)
            return fn
        return deco

    def resource(self, uri):
        def deco(fn):
            self.resources.append((uri, fn.__name__))
            return fn
        return deco


def _install_stub():
    mcp = types.ModuleType("mcp")
    mcp_server = types.ModuleType("mcp.server")
    mcp_server.MCPServer = _FakeMCPServer
    mcp.server = mcp_server
    sys.modules["mcp"] = mcp
    sys.modules["mcp.server"] = mcp_server


_install_stub()
from mcp_server import server  # noqa: E402


def test_server_registration():
    assert server.mcp.name == "fan-selector"
    assert sorted(server.mcp.tools) == ["fan_chart", "lookup_catalog", "select_fan"]
    uris = sorted(uri for uri, _ in server.mcp.resources)
    assert uris == [
        "fan://data/catalog",
        "fan://data/config",
        "fan://data/fans",
        "fan://data/impellers",
        "fan://data/motors",
    ]


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception as e:
                failures.append((name, e))
                print("FAIL", name, "->", repr(e))
    if failures:
        print("\n%d failed" % len(failures))
        sys.exit(1)
    print("\nMCP registration test passed.")
