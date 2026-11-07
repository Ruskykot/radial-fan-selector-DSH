"""Тест исполняемого контракта data/golden.json.

Для каждой точки из фикстуры сверяет run_selection() с зафиксированным эталоном:
сводку (total/passed/best) и детали прошедших (модель, Δрег, КПД, мощность, двигатель).

Запуск (из корня пакета select-radial-fan):
    python tests/test_golden_fixture.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fan_selector.select import run_selection  # noqa: E402

GOLDEN = ROOT / "data" / "golden.json"


def _load():
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_golden_fixture_summary():
    """Сводка по каждой точке совпадает с эталоном."""
    data = _load()
    assert data["version"] == 1
    assert len(data["points"]) >= 1
    for pt in data["points"]:
        res = run_selection(pt["query"])
        assert "error" not in res, (pt["query"], res.get("error"))
        s, exp = res["summary"], pt["summary"]
        assert s["total"] == exp["total"], (pt["query"], s, exp)
        assert s["passed"] == exp["passed"], (pt["query"], s, exp)
        assert s["best_model"] == exp["best_model"], (pt["query"], s, exp)
        assert (s["best_d_reg_pa"] is None) == (exp["best_d_reg_pa"] is None), (pt["query"], s, exp)
        if exp["best_d_reg_pa"] is not None:
            assert abs(s["best_d_reg_pa"] - exp["best_d_reg_pa"]) < 0.01, (pt["query"], s, exp)


def test_golden_fixture_passed_details():
    """Детали прошедших вариантов совпадают с эталоном (в порядке сортировки)."""
    data = _load()
    for pt in data["points"]:
        res = run_selection(pt["query"])
        passed = [r for r in res["results"] if r["passed"]]
        exp = pt["passed"]
        assert len(passed) == len(exp), (pt["query"], len(passed), len(exp))
        for got, want in zip(passed, exp):
            assert got["model"] == want["model"], (pt["query"], got["model"], want["model"])
            assert abs(got["d_reg_pa"] - want["d_reg_pa"]) < 0.01, (pt["query"], got, want)
            assert abs(got["eta_req"] - want["eta_req"]) < 1e-3, (pt["query"], got, want)
            assert abs(got["n_shaft_with_margin_w"] - want["n_shaft_with_margin_w"]) < 0.01, (pt["query"], got, want)
            assert got["motor"] == want["motor"], (pt["query"], got["motor"], want["motor"])


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except AssertionError as e:
                failures.append((name, e))
                print("FAIL", name, "->", e)
    if failures:
        print("\n%d failed" % len(failures))
        sys.exit(1)
    print("\nAll golden fixture tests passed.")
