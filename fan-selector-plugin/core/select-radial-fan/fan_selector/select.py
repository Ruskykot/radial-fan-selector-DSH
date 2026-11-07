"""Универсальный адаптер подбора: чистый JSON-in / JSON-out.

Единственная точка входа для любого рантайма (CLI, subprocess, MCP, тесты,
инструмент харнесса). Не содержит I/O-логики интерфейсов — только валидация
входного словаря, вызов расчётного ядра и сериализация результата.

Соглашение:
    run_selection(payload: dict) -> dict

        payload  = {q_req, p_req, pressure_type, d_reg_max?, t_air?,
                    series?, sizes?, rpms?}
        return   = {schema, query, results[], summary{}}
                    + {"error": {...}} при невалидном входе

Расчётное ядро (core.py / config.py / selector.py) НЕ модифицируется — это
гарантия неизменности качества вычислений.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .config import load_config, ConfigError
from .models import PressureType, RegulationMode, SelectionRequest, FanResult
from .repositories import load_all, load_catalog, load_vfds
from .selector import select_fans, select_fans_vfd
from .chart import chart_base64, compare_chart_base64

RESULT_SCHEMA = "fan-result/v1"
INPUT_SCHEMA = "fan-selection/v1"

_PRESSURE_ALIASES = {
    "full": PressureType.FULL,
    "static": PressureType.STATIC,
}

_REGULATION_ALIASES = {
    "throttle": RegulationMode.THROTTLE,
    "vfd": RegulationMode.VFD,
    "frequency": RegulationMode.VFD,
    "частотное": RegulationMode.VFD,
    "дроссельное": RegulationMode.THROTTLE,
}


def _as_float(value, field, default=None):
    if value is None:
        if default is not None:
            return default
        raise ValueError("Поле '%s' обязательно" % field)
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError("Поле '%s' должно быть числом, получено %r" % (field, value))


def _as_tuple(value, field):
    if value in (None, [], ()):
        return ()
    if isinstance(value, (str, int, float)):
        return (value,)
    try:
        return tuple(value)
    except TypeError:
        return (value,)


def parse_request(payload):
    """Преобразовать входной dict в SelectionRequest (с валидацией)."""
    if not isinstance(payload, dict):
        raise ValueError("Входные данные должны быть JSON-объектом")

    q_req = _as_float(payload.get("q_req"), "q_req")
    p_req = _as_float(payload.get("p_req"), "p_req")
    pressure_type = payload.get("pressure_type", "FULL")
    if isinstance(pressure_type, PressureType):
        pt = pressure_type
    else:
        key = str(pressure_type).strip().lower()
        pt = _PRESSURE_ALIASES.get(key, PressureType.FULL)

    d_reg_max = _as_float(payload.get("d_reg_max"), "d_reg_max", 1500.0)
    t_air = _as_float(payload.get("t_air"), "t_air", 20.0)

    # Режим регулирования (дроссельный / частотный) + диапазон частоты для VFD
    regulation_mode = payload.get("regulation_mode", "THROTTLE")
    if isinstance(regulation_mode, RegulationMode):
        rm = regulation_mode
    else:
        key = str(regulation_mode).strip().lower()
        rm = _REGULATION_ALIASES.get(key, RegulationMode.THROTTLE)

    freq_min_hz = _as_float(payload.get("freq_min_hz"), "freq_min_hz", 20.0)
    freq_max_hz = _as_float(payload.get("freq_max_hz"), "freq_max_hz", 60.0)

    return SelectionRequest(
        q_req=q_req,
        p_req=p_req,
        pressure_type=pt,
        d_reg_max=d_reg_max,
        t_air=t_air,
        series=_as_tuple(payload.get("series"), "series"),
        sizes=_as_tuple(payload.get("sizes"), "sizes"),
        rpms=_as_tuple(payload.get("rpms"), "rpms"),
        regulation_mode=rm,
        freq_min_hz=freq_min_hz,
        freq_max_hz=freq_max_hz,
    )


def _motor_to_dict(result):
    if result.motor is None:
        return None
    return {
        "name": result.motor.name,
        "n_kw": result.motor.n_kw,
        "n_rpm": result.motor.n_rpm,
        "i_nom": result.motor.i_nom,
    }


def _vfd_to_dict(result):
    if result.vfd is None:
        return None
    return {
        "model": result.vfd.model,
        "p_kw": result.vfd.p_kw,
        "i_nom_a": result.vfd.i_nom_a,
        "u_in": result.vfd.u_in,
        "phase": result.vfd.phase,
    }


def _result_to_dict(r, catalog=None):
    fan = r.fan
    # каталожная карточка (геометрия/масса/шум/исполнения), если найдена
    cat = _catalog_by_fan(catalog, fan) if catalog else None
    dims = cat.dims if cat else {}
    mass = cat.mass if cat else None
    noise_by_rpm = cat.noise_by_rpm if cat else {}
    executions = cat.executions if cat else []
    return {
        "model": fan.model,
        "series": fan.series,
        "size": fan.size,
        "dn": getattr(fan, "dn", None),
        "d_over_dn": getattr(fan, "d_over_dn", None),
        "max_n": fan.max_n,
        "dims": dims,
        "mass": mass,
        "executions": executions,
        "noise_by_rpm": noise_by_rpm,
        "status": r.status.value,
        "passed": r.passed,
        "d_reg_pa": round(float(r.d_reg_pa), 2),
        "eta_req": round(float(r.eta_req), 4),
        "n_shaft_with_margin_w": round(float(r.n_shaft_with_margin_w), 2),
        "n_shaft_kw": round(float(r.n_shaft_with_margin_w) / 1000.0, 4),
        "motor": _motor_to_dict(r),
        "noise_body_dba": round(float(r.noise_body_dba), 1),
        "q_work": round(float(r.q_work), 2),
        "p_work": round(float(r.p_work), 2),
        # --- VFD ---
        "regulation_mode": r.regulation_mode.value,
        "f_hz": round(float(r.f_hz), 2) if r.f_hz is not None else None,
        "n_rpm": round(float(r.n_rpm), 2) if r.n_rpm is not None else None,
        "q0": round(float(r.q0), 2) if r.q0 is not None else None,
        "n_in_w": round(float(r.n_in_w), 2) if r.n_in_w is not None else None,
        "vfd": _vfd_to_dict(r),
        "curve": {
            "q_points": list(fan.q_points),
            "p_points": list(fan.p_points),
            "q_eff": list(fan.q_eff),
            "eff_points": list(fan.eff_points),
            "q_min": fan.q_min,
            "q_max": fan.q_max,
        },
    }


def _catalog_by_fan(catalog, fan):
    """Найти каталожную карточку по (series, dn, d_over_dn)."""
    dn = getattr(fan, "dn", None)
    ddn = getattr(fan, "d_over_dn", None)
    for c in catalog:
        if c.series != fan.series:
            continue
        if dn is not None and abs(c.dn - dn) > 1e-6:
            continue
        if ddn is not None and abs(c.d_over_dn - ddn) > 1e-6:
            continue
        return c
    return None


def catalog_lookup(payload):
    """Выдать каталожную информацию по типоразмерам (геометрия/масса/шум/двигатели).

    payload = {series?, dn?, d_over_dn?}  (все необязательные фильтры)
    Возвращает {"schema": ..., "items": [...]}.
    """
    catalog = load_catalog()
    series_f = set(payload.get("series") or []) if isinstance(payload.get("series"), list) else set()
    dn_f = payload.get("dn")
    ddn_f = payload.get("d_over_dn")
    items = []
    for c in catalog:
        if series_f and c.series not in series_f:
            continue
        if dn_f is not None and abs(c.dn - float(dn_f)) > 1e-6:
            continue
        if ddn_f is not None and abs(c.d_over_dn - float(ddn_f)) > 1e-6:
            continue
        items.append({
            "series": c.series,
            "dn": c.dn,
            "d_over_dn": c.d_over_dn,
            "model": c.model,
            "max_n": c.max_n,
            "min_n_kw": c.min_n_kw,
            "max_n_kw": c.max_n_kw,
            "dims": c.dims,
            "mass": c.mass,
            "noise_by_rpm": c.noise_by_rpm,
            "executions": c.executions,
            "motors": c.motors,
            "impeller_id": c.impeller_id,
        })
    return {"schema": "fan-catalog/v1", "count": len(items), "items": items}


def chart_selection(payload):
    """Выполнить подбор и вернуть PNG-график характеристик (base64).

    payload — тот же, что и в run_selection.
    Возвращает {"schema": "fan-chart/v1", "chart_png_base64": "...", ...}.
    """
    res = run_selection(payload)
    if "error" in res:
        return res
    return {
        "schema": "fan-chart/v1",
        "summary": res["summary"],
        "query": res["query"],
        "chart_png_base64": chart_base64(res["results"], res["query"]),
        "results": res["results"],
    }


def run_selection(payload):
    """Выполнить подбор, вернуть нормализованный JSON-результат.

    Никогда не бросает исключений наружу: ошибки возвращаются как
    {"schema": ..., "error": {...}}.
    """
    try:
        req = parse_request(payload)
    except (ValueError, KeyError) as e:
        return {
            "schema": RESULT_SCHEMA,
            "error": {"code": "INVALID_INPUT", "message": str(e)},
        }

    try:
        cfg = load_config()
        fans, motors = load_all()
        if req.regulation_mode == RegulationMode.VFD:
            vfds = load_vfds()
            results = select_fans_vfd(fans, motors, vfds, req, cfg)
        else:
            results = select_fans(fans, motors, req, cfg)
        catalog = load_catalog()
    except ConfigError as e:
        return {
            "schema": RESULT_SCHEMA,
            "error": {"code": "CONFIG_ERROR", "message": str(e)},
        }

    results_list = [_result_to_dict(r, catalog) for r in results]
    passed = [r for r in results_list if r["passed"]]

    return {
        "schema": RESULT_SCHEMA,
        "query": {
            "q_req": req.q_req,
            "p_req": req.p_req,
            "pressure_type": req.pressure_type.value,
            "d_reg_max": req.d_reg_max,
            "t_air": req.t_air,
            "series": list(req.series),
            "sizes": list(req.sizes),
            "rpms": list(req.rpms),
            "regulation_mode": req.regulation_mode.value,
            "freq_min_hz": req.freq_min_hz,
            "freq_max_hz": req.freq_max_hz,
        },
        "summary": {
            "total": len(results_list),
            "passed": len(passed),
            "best_model": passed[0]["model"] if passed else None,
            "best_d_reg_pa": passed[0]["d_reg_pa"] if passed else None,
        },
        "results": results_list,
    }


def run_comparison(payload):
    """Сравнение дроссельного и частотного (ЧРП) регулирования.

    Выполняет оба расчёта для одной точки (Q, P) и возвращает их результаты
    плюс общий график сравнения. Ошибки возвращаются так же, как в run_selection.

        return = {schema: "fan-compare/v1", query,
                  throttle: {summary, results},
                  vfd:      {summary, results},
                  chart_png_base64}
    """
    throttle = run_selection({**payload, "regulation_mode": "THROTTLE"})
    if "error" in throttle:
        return throttle

    vfd = run_selection({**payload, "regulation_mode": "VFD"})
    if "error" in vfd:
        return vfd

    chart_b64 = compare_chart_base64(
        throttle["results"], vfd["results"], throttle["query"]
    )

    return {
        "schema": "fan-compare/v1",
        "query": throttle["query"],
        "throttle": {
            "summary": throttle["summary"],
            "results": throttle["results"],
        },
        "vfd": {
            "summary": vfd["summary"],
            "results": vfd["results"],
        },
        "chart_png_base64": chart_b64,
    }
