"""Проверка регистрации инструментов/ресурсов MCP-сервера (реальный SDK `mcp`).

Импортирует настоящий `mcp_server.server` (без подмены `sys.modules` заглушкой) и
проверяет, что зарегистрированы ровно 3 инструмента и 5 ресурсов с ожидаемыми
именами/URI. Логику самих инструментов проверяет tests/test_mcp.py.

Без установленного MCP SDK тест не падает и не «проходит» — он SKIP:
`pip install -r requirements-mcp.txt` (или `pip install "mcp[cli]>=2.0"`).

Запуск (из корня пакета select-radial-fan):
    python tests/test_mcp_registration.py
    pytest tests/test_mcp_registration.py   # SKIP без SDK
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Имена и URI, которые сервер обязан зарегистрировать (сверено с
# mcp_server/server.py: декораторы tool()/resource()).
EXPECTED_TOOLS = ["fan_chart", "lookup_catalog", "select_fan"]
EXPECTED_RESOURCES = [
    "fan://data/catalog",
    "fan://data/config",
    "fan://data/fans",
    "fan://data/impellers",
    "fan://data/motors",
]


def _skip_missing_sdk() -> None:
    """Пропустить тест, если MCP SDK не установлен (SKIP, не PASS и не FAIL)."""
    reason = "mcp SDK не установлен (pip install -r requirements-mcp.txt)"
    try:
        import pytest
    except ImportError:
        print("SKIP", reason)
        raise SystemExit(0)
    pytest.importorskip("mcp", reason=reason)


_skip_missing_sdk()

from mcp_server import server  # noqa: E402


def test_server_registration():
    """Сервер реально регистрирует ожидаемые инструменты и ресурсы."""
    assert server.mcp.name == "fan-selector"

    tools = getattr(server.mcp, "tools", None)
    assert tools is not None, "MCPServer не предоставляет список tools"
    registered_tools = sorted(
        t if isinstance(t, str) else getattr(t, "name", str(t)) for t in tools
    )
    assert registered_tools == EXPECTED_TOOLS, registered_tools

    resources = getattr(server.mcp, "resources", None)
    assert resources is not None, "MCPServer не предоставляет список resources"
    uris = []
    for r in resources:
        uri = getattr(r, "uri", None) or (r[0] if isinstance(r, (tuple, list)) else None)
        uris.append(str(uri))
    assert sorted(uris) == EXPECTED_RESOURCES, uris


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
