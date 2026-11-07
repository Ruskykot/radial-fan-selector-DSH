"""Smoke-тест MCP-транспорта (in-memory, реальный SDK `mcp`).

Проверяет сервер `mcp_server/server.py` целиком через MCP-клиент: список
инструментов, вызов `select_fan` (сверка с golden.json), список ресурсов и чтение
ресурса. Дополняет tests/test_mcp.py (логика) и tests/test_mcp_registration.py
(регистрация) полным прогоном по протоколу.

Требует: `pip install "mcp[cli]"` (на Windows — также `pywin32`).
Запуск (из корня пакета select-radial-fan):
    python tests/test_mcp_transport.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcp import Client  # noqa: E402
from mcp_server.server import mcp  # noqa: E402

GOLDEN = ROOT / "data" / "golden.json"


def _benchmark_summary():
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    for pt in data["points"]:
        q = pt["query"]
        if q.get("q_req") == 7500.0 and q.get("p_req") == 700.0 and q.get("pressure_type") == "FULL":
            return pt["summary"]
    raise AssertionError("эталонная точка не найдена в golden.json")


def _extract_dict(result) -> dict:
    """Достать dict из результата инструмента (structured_content или text-блок)."""
    sc = getattr(result, "structured_content", None)
    if isinstance(sc, dict):
        return sc
    for block in result.content:
        if hasattr(block, "text"):
            return json.loads(block.text)
    raise AssertionError("нет текстового контента в результате инструмента")


def _extract_text(resource_result) -> str:
    for block in resource_result.contents:
        if hasattr(block, "text"):
            return block.text
    raise AssertionError("нет текстового контента в ресурсе")


def _run():
    async def main():
        async with Client(mcp) as client:
            tools = sorted(t.name for t in (await client.list_tools()).tools)
            res = await client.call_tool(
                "select_fan", {"q_req": 7500.0, "p_req": 700.0, "pressure_type": "FULL"}
            )
            data = _extract_dict(res)
            resources = sorted(r.uri for r in (await client.list_resources()).resources)
            cfg_text = _extract_text(await client.read_resource("fan://data/config"))
            return tools, data, resources, cfg_text

    return asyncio.run(main())


def test_mcp_transport_end_to_end():
    tools, data, resources, cfg_text = _run()

    assert tools == ["fan_chart", "lookup_catalog", "select_fan"], tools

    assert data["summary"] == _benchmark_summary(), (data["summary"], _benchmark_summary())
    assert data["summary"]["passed"] == 9

    assert resources == [
        "fan://data/catalog",
        "fan://data/config",
        "fan://data/fans",
        "fan://data/impellers",
        "fan://data/motors",
    ], resources

    assert json.loads(cfg_text)["rho_air"] == 1.2


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
    print("\nAll MCP transport tests passed.")
