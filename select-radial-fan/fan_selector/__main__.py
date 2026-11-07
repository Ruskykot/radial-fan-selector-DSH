"""CLI-адаптер: python -m fan_selector --json [--chart].

Читает JSON со stdin, печатает JSON в stdout (UTF-8).

Примеры:
    echo '{"q_req":7500,"p_req":700}' | python -m fan_selector --json
    echo '{"q_req":7500,"p_req":700}' | python -m fan_selector --json --chart
"""
from __future__ import annotations

import json
import sys

from .select import run_selection, chart_selection


def _read_stdin():
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("Пустой вход: передайте JSON-объект через stdin")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Вход должен быть JSON-объектом")
    return data


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    argv = sys.argv[1:]
    if not argv or argv[0] not in ("--json", "--chart"):
        sys.stderr.write(
            "Использование: python -m fan_selector --json [--chart] < input.json"
        )
        sys.stderr.write(chr(10))
        return 2

    want_chart = "--chart" in argv or argv[0] == "--chart"

    try:
        payload = _read_stdin()
    except (ValueError, json.JSONDecodeError) as e:
        sys.stdout.write(json.dumps(
            {"schema": "fan-result/v1",
             "error": {"code": "INVALID_INPUT", "message": str(e)}},
            ensure_ascii=False,
        ))
        sys.stdout.write(chr(10))
        return 0

    result = chart_selection(payload) if want_chart else run_selection(payload)
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    sys.stdout.write(chr(10))
    return 0


if __name__ == "__main__":
    sys.exit(main())
