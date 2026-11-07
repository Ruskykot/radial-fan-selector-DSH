"""Расчётное ядро — чистые функции без I/O."""
from __future__ import annotations
import warnings
from typing import Optional, Sequence

import numpy as np

from .config import Config
from .models import (Fan, FanResult, Motor, PressureType, ResultStatus,
                     SelectionRequest)


def fit_curve(q: Sequence[float], p: Sequence[float], degree: int = 6) -> np.poly1d:
    """МНК-аппроксимация полиномом степени degree (аналог ЛИНЕЙН)."""
    q_arr = np.asarray(q, dtype=float)
    p_arr = np.asarray(p, dtype=float)
    n = len(q_arr)
    if n < 2:
        raise ValueError("Недостаточно точек для аппроксимации")
    deg = min(degree, n - 1)
    if deg < degree:
        warnings.warn(
            f"Точек ({n}) меньше, чем нужно для степени {degree}; "
            f"понижаю степень до {deg}."
        )
    return np.poly1d(np.polyfit(q_arr, p_arr, deg))


def dynamic_pressure(q_m3h: float, area_f_m2: float, rho: float = 1.2) -> float:
    """Динамическое давление при заданном расходе, Па."""
    if area_f_m2 <= 0:
        raise ValueError("Площадь выходного сечения должна быть > 0")
    v = (q_m3h / 3600.0) / area_f_m2
    return rho * v * v / 2.0


def transform_to_static(q_points: Sequence[float],
                        p_full_points: Sequence[float],
                        area_f_m2: float,
                        rho: float = 1.2) -> List[float]:
    """Перевод полной характеристики в статическую (точка-по-точке).

    Для каждой точки (Q_i, P_full_i) вычисляется своё динамическое
    давление P_dyn_i = rho * v_i^2 / 2, где v_i = Q_i / (3600 * area_f_m2).
    Затем P_stat_i = P_full_i - P_dyn_i.
    """
    result = []
    for q, p_full in zip(q_points, p_full_points):
        v = (q / 3600.0) / area_f_m2
        p_dyn = rho * v * v / 2.0
        result.append(p_full - p_dyn)
    return result


def safety_factor(n_shaft_w: float, cfg: Config) -> float:
    """Коэффициент запаса мощности по N_вала (Вт)."""
    n_kw = n_shaft_w / 1000.0
    for upper, k in cfg.safety_table:
        if n_kw < upper:
            return k
    return cfg.safety_table[-1][1]


def compute_one(fan: Fan,
                req: SelectionRequest,
                motors: Sequence[Motor],
                cfg: Config) -> FanResult:
    """Расчёт по одному вентилятору. Возвращает FanResult со статусом."""
    result = FanResult(fan=fan, status=ResultStatus.OK)

    # Проверка достаточности точек
    n_pts = min(len(fan.q_points), len(fan.p_points))
    if n_pts < 4:
        result.status = ResultStatus.INSUFFICIENT_POINTS
        result.passed = False
        return result

    # Проверка диапазона расхода
    if not (fan.q_min <= req.q_req <= fan.q_max):
        result.status = ResultStatus.OUT_OF_FLOW_RANGE
        result.passed = False
        return result

    # Аппроксимация рабочей характеристики
    if req.pressure_type == PressureType.FULL:
        poly_full = fit_curve(fan.q_points, fan.p_points, cfg.poly_degree)
        p_fan_at_q_req = float(poly_full(req.q_req))
    else:
        p_stat_points = transform_to_static(
            fan.q_points, fan.p_points, fan.area_f_m2
        )
        poly_full = fit_curve(fan.q_points, fan.p_points, cfg.poly_degree)
        poly_stat = fit_curve(fan.q_points, p_stat_points, cfg.poly_degree)
        p_fan_at_q_req = float(poly_stat(req.q_req))

    # Заполняем рабочую точку
    result.q_work = req.q_req
    result.p_work = p_fan_at_q_req

    # Проверка: кривая выше точки
    if p_fan_at_q_req < req.p_req:
        result.status = ResultStatus.CURVE_BELOW_POINT
        result.passed = False
        return result

    # Дорегулирование
    result.d_reg_pa = p_fan_at_q_req - req.p_req
    if result.d_reg_pa > req.d_reg_max:
        result.status = ResultStatus.OVER_DOR_REG
        result.passed = False
        return result

    # КПД в рабочей точке
    if not fan.q_eff or not fan.eff_points:
        result.status = ResultStatus.NO_EFFICIENCY_DATA
        result.passed = False
        return result

    eta_poly = fit_curve(fan.q_eff, fan.eff_points, min(cfg.poly_degree, 3))
    eta_at_q = float(eta_poly(req.q_req))
    result.eta_req = max(0.0, min(1.0, eta_at_q))

    # Мощность на валу (всегда по полному давлению)
    if req.pressure_type == PressureType.STATIC:
        p_dyn = dynamic_pressure(req.q_req, fan.area_f_m2, cfg.rho_air)
        p_full_pa = req.p_req + p_dyn
    else:
        p_full_pa = p_fan_at_q_req
    n_shaft_w = (req.q_req / 3600.0) * p_full_pa / max(result.eta_req, 0.01)
    result.n_shaft_with_margin_w = n_shaft_w * safety_factor(n_shaft_w, cfg)

    # Подбор двигателя
    result.motor = _select_motor(result.n_shaft_with_margin_w, motors, fan)
    if result.motor is None:
        result.status = ResultStatus.MOTOR_NOT_FOUND
        result.passed = False
        return result

    # Шум
    result.noise_body_dba = _interpolate_noise(req.q_req, fan)

    result.poly = poly_full
    result.eta_poly = eta_poly
    result.passed = True
    return result


def _select_motor(n_shaft_w: float,
                  motors: Sequence[Motor],
                  fan: Fan) -> Optional[Motor]:
    """Подобрать двигатель по мощности на валу и синхронной частоте."""
    n_shaft_kw = n_shaft_w / 1000.0
    candidates = [
        m for m in motors
        if m.n_rpm == fan.max_n
        and fan.min_n_kw <= m.n_kw <= fan.max_n_kw
        and m.n_kw >= n_shaft_kw
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda m: m.n_kw)


def _interpolate_noise(q_req: float, fan: Fan) -> float:
    """Интерполяция шума корпуса по расходу (упрощённо)."""
    if not fan.noise_body or not fan.q_points:
        return 0.0
    q_min, q_max = min(fan.q_points), max(fan.q_points)
    if q_req < q_min or q_req > q_max:
        return max(fan.noise_body) if fan.noise_body else 0.0
    t = (q_req - q_min) / (q_max - q_min) if q_max > q_min else 0.0
    idx = int(t * (len(fan.noise_body) - 1))
    return fan.noise_body[min(idx, len(fan.noise_body) - 1)]
