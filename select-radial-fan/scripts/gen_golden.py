"""Генератор исполняемого контракта data/golden.json.

Сетка рабочих точек прогоняется через run_selection() и результат фиксируется
как эталонная спека. Одна точка = {query, summary, passed[]}. Затем эта фикстура
используется для проверки всех адаптеров (ядро, MCP-сервер, React-артефакт).

Запуск (из корня пакета select-radial-fan, bundled Python):
    python scripts/gen_golden.py

Перегенерировать фикстуру следует ТОЛЬКО осознанно — после изменения данных/ядра,
с обоснованием в коммите (аналогично golden-тестам).
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from fan_selector.select import run_selection  # noqa: E402

# Сетка: покрытие FULL/STATIC, разные диапазоны Q/P, фильтры, пустой результат.
POINTS = [
    # Полное давление
    {"q_req": 7500.0, "p_req": 700.0, "pressure_type": "FULL"},          # эталон
    {"q_req": 2000.0, "p_req": 400.0, "pressure_type": "FULL"},          # низкий Q
    {"q_req": 12000.0, "p_req": 900.0, "pressure_type": "FULL"},         # средний Q
    {"q_req": 50000.0, "p_req": 1500.0, "pressure_type": "FULL"},        # высокий Q
    {"q_req": 300.0, "p_req": 80.0, "pressure_type": "FULL"},            # очень низкий Q
    {"q_req": 7500.0, "p_req": 9000.0, "pressure_type": "FULL"},         # чрезмерное P (passed=0)
    {"q_req": 15000.0, "p_req": 500.0, "pressure_type": "FULL",
     "series": ["ВР 86-77"]},                                            # фильтр по серии
    # Статическое давление
    {"q_req": 5000.0, "p_req": 800.0, "pressure_type": "STATIC"},        # существующий тест
    {"q_req": 7500.0, "p_req": 700.0, "pressure_type": "STATIC"},        # эталон STATIC
    {"q_req": 15000.0, "p_req": 1000.0, "pressure_type": "STATIC"},      # высокий Q STATIC
    {"q_req": 10000.0, "p_req": 400.0, "pressure_type": "STATIC",
     "rpms": [1500, 3000]},                                              # фильтр по оборотам
]


def _passed_entry(r):
    return {
        "model": r["model"],
        "d_reg_pa": r["d_reg_pa"],
        "eta_req": r["eta_req"],
        "n_shaft_with_margin_w": r["n_shaft_with_margin_w"],
        "motor": r["motor"],
    }


def main():
    points = []
    for query in POINTS:
        res = run_selection(query)
        if "error" in res:
            points.append({"query": query, "error": res["error"]})
            continue
        points.append({
            "query": query,
            "summary": res["summary"],
            "passed": [_passed_entry(r) for r in res["results"] if r["passed"]],
        })

    out = {"version": 1, "points": points}
    target = os.path.join(ROOT, "data", "golden.json")
    with open(target, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("wrote %s (%d points)" % (target, len(points)))


if __name__ == "__main__":
    main()
