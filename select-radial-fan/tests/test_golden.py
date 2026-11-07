"""Golden-тесты: фиксируют численный результат подбора.

Гарантия неизменности качества расчётов при любой переработке интерфейсов.
Запуск: python tests/test_golden.py  (работ. каталог — корень проекта).

Справочники: 66 вентиляторов (лист 1), 55 двигателей (лист 1_1),
31 каталожная карточка массо-габаритов (лист 1_2).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fan_selector.select import run_selection, catalog_lookup, chart_selection
from fan_selector.repositories import load_fans, load_motors, load_catalog


def test_catalog_counts():
    """Справочники загружены в ожидаемых объёмах."""
    assert len(load_fans()) == 66, len(load_fans())
    assert len(load_motors()) == 55, len(load_motors())
    assert len(load_catalog()) == 31, len(load_catalog())


def test_full_pressure_benchmark():
    """Q=7500, P=700, полное давление — эталон."""
    res = run_selection({"q_req": 7500.0, "p_req": 700.0, "pressure_type": "FULL"})
    assert "error" not in res, res.get("error")
    s = res["summary"]
    assert s["total"] == 10, s
    assert s["passed"] == 9, s
    assert s["best_model"] == "ВР 280-46-6.3(1DN)-Y-X/750", s
    best = [r for r in res["results"] if r["passed"]][0]
    assert abs(best["d_reg_pa"] - 47.56) < 0.01, best["d_reg_pa"]
    assert abs(best["eta_req"] - 0.6292) < 1e-3, best["eta_req"]
    assert abs(best["n_shaft_with_margin_w"] - 2846.61) < 0.01, best["n_shaft_with_margin_w"]
    assert best["motor"]["name"] == "160S8", best["motor"]
    assert best["motor"]["n_kw"] == 7.5
    assert best["motor"]["n_rpm"] == 750


def test_catalog_enrichment():
    """Результат обогащён каталожными массо-габаритами и исполнениями."""
    res = run_selection({"q_req": 7500.0, "p_req": 700.0})
    best = [r for r in res["results"] if r["passed"]][0]
    assert best["dims"]["D"] == 630.0, best["dims"]
    assert best["mass"] == 328.2, best["mass"]
    assert "О" in best["executions"], best["executions"]
    assert "V" in best["executions"], best["executions"]
    assert best["noise_by_rpm"]["750"][-1] == 93.0, best["noise_by_rpm"]


def test_invalid_missing_field():
    """Отсутствующее обязательное поле возвращает INVALID_INPUT, не падает."""
    res = run_selection({"q_req": 7500})
    assert res["error"]["code"] == "INVALID_INPUT"


def test_static_pressure_deterministic():
    """Статическое давление — детерминированный результат без исключений."""
    res = run_selection({"q_req": 5000.0, "p_req": 800.0, "pressure_type": "STATIC"})
    assert "error" not in res
    assert res["summary"]["total"] == 10


def test_curve_points_present():
    """Каждый результат несёт точки кривой для визуализации харнессом."""
    res = run_selection({"q_req": 7500.0, "p_req": 700.0})
    for r in res["results"]:
        assert "curve" in r and r["curve"]["q_points"], r["model"]


def test_chart_generation():
    """График характеристик строится (base64 PNG)."""
    import base64
    res = chart_selection({"q_req": 7500.0, "p_req": 700.0})
    assert res["schema"] == "fan-chart/v1"
    assert "chart_png_base64" in res
    assert len(res["chart_png_base64"]) > 1000
    png = base64.b64decode(res["chart_png_base64"])
    assert png[:8] == b"\x89PNG\r\n\x1a\n", "PNG signature"


def test_catalog_lookup_filter():
    """catalog_lookup фильтрует по серии/DN/D-DN."""
    items = catalog_lookup({"series": ["ВР 86-77"], "dn": 6.3})
    assert items["count"] >= 1
    for it in items["items"]:
        assert it["series"] == "ВР 86-77"
        assert abs(it["dn"] - 6.3) < 1e-6
        assert "executions" in it


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
            except Exception as e:
                failures.append((name, e))
                print("ERROR", name, "->", repr(e))
    if failures:
        print("\n%d failed" % len(failures))
        sys.exit(1)
    print("\nAll golden tests passed.")
