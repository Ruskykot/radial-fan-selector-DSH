"""Тонкий REST-фолбэк для React-артефакта и DSH-плагина (только stdlib).

Эндпоинты:
- POST /select, /chart, /compare, /catalog — расчётное ядро;
- GET /health — проверка живости;
- GET/POST/DELETE /history — локальная история подборов этого REST-сервера.
  Файл `.fan-selector-history.json` в корне проекта, лимит 50 записей, путь
  переопределяется FAN_HISTORY_PATH. Хранилище независимое — плагин DSH ведёт
  свою историю (`~/.fan-selector-history.json`, лимит 5000) через
  инструмент `fan_selector_history`.

Порт 8001 (переопределяется FAN_REST_PORT).
"""
from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from fan_selector.repositories import DATA_DIR
from fan_selector.select import run_selection, run_comparison, catalog_lookup, chart_selection

PORT = int(os.environ.get("FAN_REST_PORT", "8001"))
HISTORY_CAP = 50
# История живёт в корне рабочей области (не в data/ — каталог справочных данных
# доступен только для чтения). Переопределяется через FAN_HISTORY_PATH.
HISTORY_PATH = os.environ.get(
    "FAN_HISTORY_PATH",
    os.path.join(os.path.dirname(os.path.dirname(DATA_DIR)), ".fan-selector-history.json"),
)
_HISTORY_LOCK = threading.Lock()


def _load_history() -> list:
    with _HISTORY_LOCK:
        try:
            with open(HISTORY_PATH, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []


def _save_history(entries: list) -> None:
    with _HISTORY_LOCK:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "POST, GET, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"ok": True})
        elif self.path == "/history":
            self._json({"items": _load_history()})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n)
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            self._json({"error": {"code": "INVALID_INPUT", "message": "invalid json"}}, 400)
            return

        if self.path == "/select":
            self._json(run_selection(payload))
        elif self.path == "/chart":
            self._json(chart_selection(payload))
        elif self.path == "/compare":
            self._json(run_comparison(payload))
        elif self.path == "/catalog":
            self._json(catalog_lookup(payload))
        elif self.path == "/history":
            entries = _load_history()
            entries = [e for e in entries if e.get("id") != payload.get("id")]
            entries.insert(0, payload)
            entries = entries[:HISTORY_CAP]
            _save_history(entries)
            self._json({"items": entries})
        else:
            self._json({"error": "not found"}, 404)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/history":
            self._json({"error": "not found"}, 404)
            return
        qs = parse_qs(parsed.query)
        entry_id = qs.get("id", [None])[0]
        entries = _load_history()
        if entry_id:
            entries = [e for e in entries if e.get("id") != entry_id]
        else:
            entries = []
        _save_history(entries)
        self._json({"items": entries})

    def log_message(self, *args) -> None:  # тихо
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
