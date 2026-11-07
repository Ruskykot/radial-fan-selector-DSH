"""MCP-сервер подбора радиальных вентиляторов.

Тонкий адаптер над существующим ядром `fan_selector`: регистрирует функции из
`mcp_server.tools` как типизированные инструменты (`select_fan`, `lookup_catalog`,
`fan_chart`) и справочники как ресурсы `fan://data/*`. Ядро не меняется.

Запуск (после `pip install "mcp[cli]"`, из корня пакета select-radial-fan):
    python -m mcp run mcp_server/server.py --transport stdio
    python -m mcp run mcp_server/server.py --transport streamable-http
"""
from __future__ import annotations

from mcp.server import MCPServer

from . import tools

mcp = MCPServer("fan-selector")

mcp.tool()(tools.select_fan)
mcp.tool()(tools.lookup_catalog)
mcp.tool()(tools.fan_chart)
mcp.resource("fan://data/fans")(tools.data_fans)
mcp.resource("fan://data/impellers")(tools.data_impellers)
mcp.resource("fan://data/motors")(tools.data_motors)
mcp.resource("fan://data/catalog")(tools.data_catalog)
mcp.resource("fan://data/config")(tools.data_config)
