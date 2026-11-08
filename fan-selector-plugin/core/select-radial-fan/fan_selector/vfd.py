"""Расчёт частотного регулирования (ЧРП / VFD) — чистые функции.

Реализует режим подбора по частоте вращения по законам подобия
(расход ∝ n, давление ∝ n², мощность ∝ n³) и подбор реального частотного
преобразователя по параметрам подобранного двигателя. См. docs/CALCULATION_VFD.md
(исходное ТЗ, по которому писался модуль, — docs/archive/VFD_TZ.md).

Существующий модуль core.py (дроссельный режим) НЕ модифицируется.
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

from .config import Config
from .core import fit_curve, safety_factor, _select_motor, _interpolate_noise
from .models import (Fan, FanResult, Motor, RegulationMode, ResultStatus,
                     SelectionRequest, Vfd)


def network_intersection(fan: Fan, k: float, cfg: Config) -> Optional[float]:
    """Найти Q₀ — точку пересечения номинальной кривой P_nom(Q) и параболы сети k·Q².

    Решается уравнение g(Q) = P_nom(Q) − k·Q² = 0 численно: скан по диапазону
    [q_min, q_max] с поиском смены знака, затем бисекция.

    Args:
        fan: Вентилятор (номинальная кривая Q-P).
        k: Коэффициент сети k = P_req / Q_req².
        cfg: Конфигурация.

    Returns:
        Q₀, м³/ч, или None, если пересечения нет.
    """
    poly = fit_curve(fan.q_points, fan.p_points, cfg.poly_degree)

    def g(q: float) -> float:
        return float(poly(q)) - k * q * q

    q_min, q_max = fan.q_min, fan.q_max
    if q_max <= q_min:
        return None

    n = 240
    qs = np.linspace(q_min, q_max, n)
    bracket = None
    prev_q, prev_g = qs[0], g(qs[0])
    for q in qs[1:]:
        cur_g = g(q)
        if cur_g == 0.0:
            return float(q)
        if prev_g * cur_g < 0:
            bracket = (prev_q, q)
            break
        prev_q, prev_g = q, cur_g

    if bracket is None:
        return None

    a, b = bracket
    ga = g(a)
    for _ in range(80):
        m = (a + b) / 2.0
        gm = g(m)
        if ga * gm <= 0:
            b = m
        else:
            a = m
            ga = gm
    return float((a + b) / 2.0)


def select_vfd(motor: Optional[Motor], vfds: Sequence[Vfd], fan: Fan) -> Optional[Vfd]:
    """Подобрать ЧРП по параметрам двигателя.

    Критерии (docs/CALCULATION_VFD.md, п. 4.7; исходное ТЗ — docs/archive/VFD_TZ.md):
    1. u_in совпадает с напряжением двигателя (fan.voltage).
    2. p_kw ≥ мощности двигателя (motor.n_kw).
    3. i_nom_a ≥ номинального тока двигателя (если ток известен).
    Выбирается ЧРП с минимальной достаточной мощностью.
    """
    if motor is None:
        return None
    candidates = [
        v for v in vfds
        if v.u_in == fan.voltage
        and v.p_kw >= motor.n_kw
        and (motor.i_nom is None or v.i_nom_a >= motor.i_nom)
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda v: v.p_kw)


def compute_vfd_one(fan: Fan,
                    req: SelectionRequest,
                    motors: Sequence[Motor],
                    vfds: Sequence[Vfd],
                    cfg: Config) -> FanResult:
    """Расчёт VFD для одного вентилятора. Возвращает FanResult со статусом."""
    result = FanResult(fan=fan, status=ResultStatus.OK, regulation_mode=RegulationMode.VFD)

    n_pts = min(len(fan.q_points), len(fan.p_points))
    if n_pts < 4:
        result.status = ResultStatus.INSUFFICIENT_POINTS
        result.passed = False
        return result

    if not (fan.q_min <= req.q_req <= fan.q_max):
        result.status = ResultStatus.OUT_OF_FLOW_RANGE
        result.passed = False
        return result

    # ФР-02: коэффициент сети
    k = req.p_req / (req.q_req * req.q_req)

    # ФР-03: пересечение номинальной кривой и сети
    q0 = network_intersection(fan, k, cfg)
    if q0 is None or q0 <= 0:
        result.status = ResultStatus.NO_NETWORK_INTERSECTION
        result.passed = False
        return result

    # ФР-04/05: относительная частота, Гц, обороты
    f = req.q_req / q0
    f_hz = f * cfg.vfd.f_nom_hz
    n_rpm = f * fan.max_n

    # ФР-06: диапазон частоты
    if f_hz < req.freq_min_hz:
        result.status = ResultStatus.FREQ_BELOW_MIN
        result.passed = False
        return result
    if f_hz > req.freq_max_hz:
        result.status = ResultStatus.FREQ_ABOVE_MAX
        result.passed = False
        return result

    # ФР-07: КПД подобием (смещение точки по расходу)
    if not fan.q_eff or not fan.eff_points:
        result.status = ResultStatus.NO_EFFICIENCY_DATA
        result.passed = False
        return result
    eta_poly = fit_curve(fan.q_eff, fan.eff_points, min(cfg.poly_degree, 3))
    eta_f = float(eta_poly(req.q_req / f))
    result.eta_req = max(0.0, min(1.0, eta_f))

    # ФР-08: мощность на валу
    n_shaft_w = (req.q_req / 3600.0) * req.p_req / max(result.eta_req, 0.01)
    result.n_shaft_with_margin_w = n_shaft_w * safety_factor(n_shaft_w, cfg)

    result.f_hz = round(f_hz, 2)
    result.n_rpm = round(n_rpm, 2)
    result.q0 = round(q0, 2)
    result.q_work = req.q_req
    result.p_work = req.p_req

    # ФР-10: двигатель (существующая логика по номинальной частоте)
    result.motor = _select_motor(result.n_shaft_with_margin_w, motors, fan)
    if result.motor is None:
        result.status = ResultStatus.MOTOR_NOT_FOUND
        result.passed = False
        return result

    # ФР-09: потребляемая мощность
    result.n_in_w = round(
        result.n_shaft_with_margin_w / (cfg.vfd.eta_vfd * cfg.vfd.eta_motor_part_load), 2
    )

    # ФР-11: частотный преобразователь
    result.vfd = select_vfd(result.motor, vfds, fan)
    if result.vfd is None:
        result.status = ResultStatus.VFD_NOT_FOUND
        result.passed = False
        return result

    result.noise_body_dba = _interpolate_noise(req.q_req, fan)
    result.passed = True
    return result
