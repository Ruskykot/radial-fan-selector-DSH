"""Запуск MCP-сервера по stdio: `python -m mcp_server` (из корня пакета)."""
from .server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
