"""Smoke-тест REST-фолбэка (mcp_server/rest.py) — in-process.

Поднимает ThreadingHTTPServer в потоке и проверяет /select (эталон), /catalog,
обработку невалидного JSON и пропущенного обязательного поля. Это доказательство
рабочего пути «ядро → REST API», который использует React-артефакт.

Запуск (из корня пакета select-radial-fan):
    python tests/test_rest.py
"""
from __future__ import annotations

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcp_server.rest import Handler, PORT  # noqa: E402


def _server():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.25)
    return srv


def _post(path, payload):
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))


def test_rest_select_benchmark():
    srv = _server()
    try:
        res = _post("/select", {"q_req": 7500.0, "p_req": 700.0, "pressure_type": "FULL"})
        assert res["summary"]["total"] == 10
        assert res["summary"]["passed"] == 9
        assert res["summary"]["best_model"] == "ВР 280-46-6.3(1DN)-Y-X/750"
        assert res["summary"]["best_d_reg_pa"] == 47.56
    finally:
        srv.shutdown()


def test_rest_catalog_filter():
    srv = _server()
    try:
        res = _post("/catalog", {"series": ["ВР 86-77"], "dn": 6.3})
        assert res["count"] >= 1
        for it in res["items"]:
            assert it["series"] == "ВР 86-77"
            assert abs(it["dn"] - 6.3) < 1e-6
    finally:
        srv.shutdown()


def test_rest_missing_field_returns_error():
    srv = _server()
    try:
        res = _post("/select", {"q_req": 7500.0})
        assert res["error"]["code"] == "INVALID_INPUT"
    finally:
        srv.shutdown()


def test_rest_invalid_json_400():
    srv = _server()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{PORT}/select", data=b"{bad json", method="POST"
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            raise AssertionError("ожидался HTTP 400")
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        srv.shutdown()


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
    print("\nAll REST smoke tests passed.")
