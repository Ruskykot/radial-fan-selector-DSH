"""Запуск REST-фолбэка ядра fan_selector на заданном порту (для DSH-плагина).

    python run-rest.py 8100

Пакет fan_selector ищется через FAN_SELECTOR_CORE, рядом (select-radial-fan/)
или как установленный pip-пакет.
"""
import os
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path

_core = os.environ.get("FAN_SELECTOR_CORE")
if _core and Path(_core).is_dir():
    sys.path.insert(0, _core)
elif (Path(__file__).resolve().parent / "select-radial-fan").is_dir():
    sys.path.insert(0, str(Path(__file__).resolve().parent / "select-radial-fan"))

from mcp_server.rest import Handler  # noqa: E402

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8100
print(f"fan-selector REST on http://127.0.0.1:{port}", flush=True)
ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
