"""Тесты MCP-адаптера (логика инструментов, без SDK `mcp`).

Проверяет функции из `mcp_server.tools` — ту самую логику, которую `server.py`
регистрирует как инструменты/ресурсы MCP. Сверка с исполняемым контрактом
`data/golden.json`.

Полный smoke-тест транспорта (JSON-RPC stdio/HTTP) требует SDK и запущенного
сервера — выполняется вручную: `pip install "mcp[cli]"`, затем
`python -m mcp dev mcp_server/server.py` (MCP Inspector).

Запуск (из корня пакета select-radial-fan):
    python tests/test_mcp.py
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcp_server import tools  # noqa: E402

GOLDEN = ROOT / "data" / "golden.json"


def _benchmark_point():
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    for pt in data["points"]:
        q = pt["query"]
        if q.get("q_req") == 7500.0 and q.get("p_req") == 700.0 and q.get("pressure_type") == "FULL":
            return pt
    raise AssertionError("эталонная точка не найдена в golden.json")


def test_select_fan_matches_golden():
    pt = _benchmark_point()
    res = tools.select_fan(7500.0, 700.0, "FULL")
    assert "error" not in res, res.get("error")
    assert res["summary"] == pt["summary"], (res["summary"], pt["summary"])
    passed = [r for r in res["results"] if r["passed"]]
    assert len(passed) == len(pt["passed"])
    assert passed[0]["model"] == pt["passed"][0]["model"]


def test_select_fan_with_filters():
    res = tools.select_fan(15000.0, 500.0, "FULL", series=["ВР 86-77"])
    assert "error" not in res, res.get("error")
    for r in res["results"]:
        assert r["series"] == "ВР 86-77", r["series"]


def test_lookup_catalog_filter():
    res = tools.lookup_catalog(series=["ВР 86-77"], dn=6.3)
    assert res["count"] >= 1
    for it in res["items"]:
        assert it["series"] == "ВР 86-77"
        assert abs(it["dn"] - 6.3) < 1e-6


def test_fan_chart_png():
    res = tools.fan_chart(7500.0, 700.0, "FULL")
    assert res["schema"] == "fan-chart/v1"
    png = base64.b64decode(res["chart_png_base64"])
    assert png[:8] == b"\x89PNG\r\n\x1a\n", "PNG signature"


def test_data_resources_readable():
    assert isinstance(json.loads(tools.data_fans()), list)
    assert isinstance(json.loads(tools.data_motors()), list)
    cfg = json.loads(tools.data_config())
    assert cfg["rho_air"] == 1.2


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
    print("\nAll MCP tool tests passed.")
