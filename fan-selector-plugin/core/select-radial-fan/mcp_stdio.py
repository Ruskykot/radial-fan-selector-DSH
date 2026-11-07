"""Экспериментальный запуск MCP-сервера (stdio или streamable-http).

ВНИМАНИЕ: экспериментальный MCP-слой: API и запуск могут меняться, поддержка не
гарантирована.

Запуск (не зависит от рабочего каталога):
    python mcp_stdio.py                  # stdio
    python mcp_stdio.py streamable-http  # http://127.0.0.1:8000/mcp
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server.server import mcp  # noqa: E402


def run_streamable_http(host: str = "127.0.0.1", port: int = 8000) -> None:
    import uvicorn

    app = mcp.streamable_http_app(streamable_http_path="/mcp", host=host)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    if transport == "streamable-http":
        run_streamable_http()
    else:
        mcp.run(transport="stdio")
