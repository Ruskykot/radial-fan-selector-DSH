"""Построение PNG-графика аэродинамических характеристик (без matplotlib).

Использует Pillow + numpy (обе зависимости доступны). Рисует кривые P(Q),
кривую сети и рабочую точку. Возвращает PNG-байты/base64.

Режим сравнения (render_compare_chart) рисует для каждого вентилятора ДВЕ
кривые: дроссельную (сплошная) и приведённую при частоте f (пунктирная), —
одного цвета и одной толщины, а в легенде пары идут последовательно.
"""
from __future__ import annotations

import base64
import io
import math
from typing import Dict, List, Optional, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _fit_poly(q: Sequence[float], p: Sequence[float], degree: int = 6):
    """МНК-полином P(Q). Возвращает None при нехватке точек."""
    q = np.asarray(q, dtype=float)
    p = np.asarray(p, dtype=float)
    if len(q) < 2 or len(p) < 2:
        return None
    deg = min(degree, len(q) - 1)
    try:
        return np.poly1d(np.polyfit(q, p, deg))
    except Exception:
        return None


def _load_font(size: int):
    """Системный шрифт с кириллицей; fallback — дефолтный."""
    for path in (r"C:\Windows\Fonts\arial.ttf",
                 r"C:\Windows\Fonts\segoeui.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _nice_scale(max_val: float):
    """Подобрать «красивый» шаг (кратный 500) и округлённый максимум оси.

    Базовый шаг — 500; если делений получается слишком много (> 12), шаг
    укрупняется (1000, 2000, 5000, …). Возвращает (step, ceil_max).
    """
    if max_val <= 0:
        return 500.0, 500.0
    for step in (500.0, 1000.0, 2000.0, 5000.0, 10000.0, 20000.0,
                 50000.0, 100000.0, 200000.0):
        if max_val / step <= 12:
            return step, step * math.ceil(max_val / step)
    step = 500000.0
    return step, step * math.ceil(max_val / step)


def _dashed_line(d, pts, fill, dash: int = 6, width: int = 1):
    """Пунктирная линия по точкам."""
    on = True
    for a, b in zip(pts, pts[1:]):
        if on:
            d.line([a, b], fill=fill, width=width)
        on = not on


def _dash_swatch(d, x0: float, x1: float, y: float, color, width: int = 2,
                 dash: int = 4, gap: int = 3):
    """Образец пунктира для легенды сравнения."""
    x = x0
    while x < x1:
        xe = min(x + dash, x1)
        d.line([(x, y), (xe, y)], fill=color, width=width)
        x += dash + gap


def _plot_frame(q_req: float, p_req: float, raw_x_max: float,
                raw_y_max: float, width: int = 1000, height: int = 620,
                right_pad: int = 20):
    """Создать холст и нарисовать оси, сетку, подписи и кривую сети.

    right_pad — ширина правого поля (для вынесенной легенды сравнения).
    Возвращает словарь с контекстом рисования (img/d/px/шрифты/геометрия).
    """
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)

    ml, mr, mt, mb = 90, right_pad, 20, 70  # поля
    plot_w = width - ml - mr
    plot_h = height - mt - mb

    if raw_x_max <= 0:
        raw_x_max = 1
    if raw_y_max <= 0:
        raw_y_max = 1
    raw_x_max *= 1.05
    raw_y_max *= 1.10

    # «красивые» шаг (кратный 500) и округлённый вверх максимум осей
    x_step, x_max = _nice_scale(raw_x_max)
    y_step, y_max = _nice_scale(raw_y_max)

    def px(x, y):
        return (ml + x / x_max * plot_w, mt + (1 - y / y_max) * plot_h)

    font_s = _load_font(13)
    font_t = _load_font(15)

    # оси
    d.line([(ml, mt), (ml, mt + plot_h)], fill=(60, 60, 60), width=2)
    d.line([(ml, mt + plot_h), (ml + plot_w, mt + plot_h)], fill=(60, 60, 60), width=2)

    # очень тонкая серая сетка + подписи делений по X
    v = 0.0
    while v <= x_max + 1e-9:
        gx = ml + v / x_max * plot_w
        d.line([(gx, mt), (gx, mt + plot_h)], fill=(233, 233, 233))
        d.line([(gx, mt + plot_h), (gx, mt + plot_h + 4)], fill=(60, 60, 60))
        d.text((gx - 18, mt + plot_h + 8), "%.0f" % v, fill=(40, 40, 40), font=font_s)
        v += x_step

    # очень тонкая серая сетка + подписи делений по Y
    v = 0.0
    while v <= y_max + 1e-9:
        gy = mt + (1 - v / y_max) * plot_h
        d.line([(ml, gy), (ml + plot_w, gy)], fill=(233, 233, 233))
        d.line([(ml - 4, gy), (ml, gy)], fill=(60, 60, 60))
        d.text((6, gy - 8), "%.0f" % v, fill=(40, 40, 40), font=font_s)
        v += y_step

    # подписи осей
    d.text((ml + plot_w / 2 - 40, height - mb + 34), "Q, m3/h", fill=(0, 0, 0), font=font_t)
    d.text((ml + 4, 2), "P, Pa", fill=(0, 0, 0), font=font_t)

    # кривая сети P = k Q^2
    if q_req > 0:
        k = p_req / (q_req ** 2)
        q_net = np.linspace(0, x_max, 100)
        p_net = k * q_net ** 2
        pts = [px(float(a), float(b)) for a, b in zip(q_net, p_net)]
        _dashed_line(d, pts, fill=(120, 120, 120), dash=6)

    return {
        "img": img, "d": d, "px": px,
        "font_s": font_s, "font_t": font_t,
        "ml": ml, "mt": mt, "plot_w": plot_w, "plot_h": plot_h,
        "x_max": x_max, "y_max": y_max,
        "q_req": q_req, "p_req": p_req,
    }


def _draw_working_point(d, px, q_req: float, p_req: float,
                        ml: float, mt: float, plot_h: float) -> None:
    """Рабочая точка (красный кружок) с выносками к осям."""
    wx, wy = px(q_req, p_req)
    d.ellipse([(wx - 6, wy - 6), (wx + 6, wy + 6)], outline=(200, 30, 30), width=3)
    d.line([(wx, wy), (wx, mt + plot_h)], fill=(200, 30, 30), width=1)
    d.line([(ml, wy), (wx, wy)], fill=(200, 30, 30), width=1)


def _png(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_chart(results: List[dict], req: dict,
                 width: int = 1000, height: int = 620,
                 vfd_results: Optional[List[dict]] = None) -> bytes:
    """Построить PNG-график одного режима. results — список dict из run_selection.

    Если передан vfd_results или req.regulation_mode == VFD, дополнительно
    рисуется приведённая кривая лучшего вентилятора при частоте f.
    """
    q_req = float(req.get("q_req", 0.0))
    p_req = float(req.get("p_req", 0.0))

    # диапазоны осей (сырые, с запасом)
    raw_x_max = max([q_req] + [r.get("curve", {}).get("q_max") or 0 for r in results])
    raw_y_max = max([p_req] + [max(r.get("curve", {}).get("p_points") or [0]) for r in results])

    fr = _plot_frame(q_req, p_req, raw_x_max, raw_y_max, width, height)
    d, px = fr["d"], fr["px"]
    font_s = fr["font_s"]
    ml, mt, plot_h = fr["ml"], fr["mt"], fr["plot_h"]

    # приведённая кривая лучшего вентилятора при частоте f (режим VFD / сравнение)
    vfd_source = vfd_results if vfd_results is not None else (
        results if req.get("regulation_mode") == "VFD" else None
    )
    if vfd_source:
        best_vfd = next((r for r in vfd_source if r.get("passed") and r.get("f_hz")), None)
        if best_vfd:
            curve = best_vfd.get("curve") or {}
            qp = curve.get("q_points") or []
            pp = curve.get("p_points") or []
            poly = _fit_poly(qp, pp, 6)
            f_hz = float(best_vfd.get("f_hz") or 0.0)
            f_rel = f_hz / 50.0
            if poly is not None and f_rel > 0 and qp:
                q_plot = np.linspace(0.0, max(qp) * f_rel, 160)
                p_plot = (f_rel ** 2) * poly(q_plot / f_rel)
                pts = [px(float(a), float(b)) for a, b in zip(q_plot, p_plot)]
                _dashed_line(d, pts, fill=(30, 120, 220), dash=5)

    # кривые вентиляторов
    legend = []
    passed_colors = [(30, 120, 220), (220, 90, 30), (40, 160, 80), (140, 70, 190)]
    for i, r in enumerate(results):
        curve = r.get("curve") or {}
        qp = curve.get("q_points") or []
        pp = curve.get("p_points") or []
        if not qp or not pp:
            continue
        poly = _fit_poly(qp, pp, 6)
        if poly is None:
            continue
        q_plot = np.linspace(min(qp), max(qp), 200)
        p_plot = poly(q_plot)
        pts = [px(float(a), float(b)) for a, b in zip(q_plot, p_plot)]
        if r.get("passed"):
            color = passed_colors[i % len(passed_colors)]
            d.line(pts, fill=color, width=2)
            legend.append((color, r.get("model", "")))
        else:
            _dashed_line(d, pts, fill=(200, 200, 200), dash=4)

    # рабочая точка
    _draw_working_point(d, px, q_req, p_req, ml, mt, plot_h)

    # легенда (прошедшие)
    if legend:
        ly = mt + 8
        for color, model in legend[:8]:
            d.rectangle([(ml + 8, ly), (ml + 24, ly + 12)], fill=color)
            d.text((ml + 30, ly - 2), model[:44], fill=(30, 30, 30), font=font_s)
            ly += 16

    return _png(fr["img"])


def chart_base64(results: List[dict], req: dict) -> str:
    """PNG → base64 (для встраивания в ответ)."""
    return base64.b64encode(render_chart(results, req)).decode("ascii")


# --- режим сравнения: пары «дроссель (сплошная) / ЧРП (пунктир)» ----------

# палитра: каждому вентилятору — свой цвет, обе его кривые одного цвета
_COMPARE_COLORS = [
    (30, 120, 220), (220, 90, 30), (40, 160, 80), (140, 70, 190),
    (200, 30, 120), (0, 150, 150), (180, 140, 0), (90, 90, 210),
    (150, 60, 60), (60, 160, 60), (200, 120, 0), (80, 80, 80),
]


def _nominal_curve(result: Optional[dict]):
    """Номинальная (дроссельная) кривая вентилятора: (q, p) или None."""
    if result is None:
        return None
    curve = result.get("curve") or {}
    qp = curve.get("q_points") or []
    pp = curve.get("p_points") or []
    if len(qp) < 2 or len(pp) < 2:
        return None
    poly = _fit_poly(qp, pp, 6)
    if poly is None:
        return None
    q_plot = np.linspace(float(min(qp)), float(max(qp)), 220)
    return q_plot, poly(q_plot)


def _reduced_curve(result: Optional[dict]):
    """Приведённая (ЧРП) кривая при частоте f: (q, p) или None.

    Законы подобия: q_red = f_rel · q, p_red = f_rel² · P_nom(q).
    Кривая проходит через рабочую точку (Q_req, P_req).
    """
    if result is None:
        return None
    curve = result.get("curve") or {}
    qp = curve.get("q_points") or []
    pp = curve.get("p_points") or []
    if len(qp) < 2 or len(pp) < 2:
        return None
    poly = _fit_poly(qp, pp, 6)
    try:
        f_hz = float(result.get("f_hz") or 0.0)
    except (TypeError, ValueError):
        f_hz = 0.0
    f_rel = f_hz / 50.0
    if poly is None or f_rel <= 0:
        return None
    q_base = np.linspace(float(min(qp)), float(max(qp)), 220)
    return q_base * f_rel, (f_rel ** 2) * poly(q_base)


def render_compare_chart(throttle_results: List[dict],
                         vfd_results: List[dict],
                         req: dict,
                         width: int = 1320, height: int = 760) -> bytes:
    """Общий график сравнения: для каждого вентилятора — дроссельная кривая
    (сплошная) и приведённая кривая ЧРП (пунктирная) одного цвета и толщины.

    Легенда вынесена в правую панель и перечисляет пары последовательно:
    сначала «(дроссель)», затем «(ЧРП)» для того же вентилятора.
    """
    q_req = float(req.get("q_req", 0.0))
    p_req = float(req.get("p_req", 0.0))

    t_by_model = {r.get("model"): r for r in (throttle_results or [])}
    v_by_model = {r.get("model"): r for r in (vfd_results or [])}

    # те же вентиляторы в обоих режимах: сначала прошедшие в дроссельном
    # (в его порядке), затем прошедшие только в ЧРП
    models: List[str] = []
    seen = set()
    for r in (throttle_results or []):
        m = r.get("model")
        if r.get("passed") and m not in seen:
            seen.add(m)
            models.append(m)
    for r in (vfd_results or []):
        m = r.get("model")
        if r.get("passed") and m not in seen:
            seen.add(m)
            models.append(m)

    items = []
    raw_x_max = q_req
    raw_y_max = p_req
    for m in models:
        t_curve = _nominal_curve(t_by_model.get(m))
        v_curve = _reduced_curve(v_by_model.get(m))
        if t_curve is not None:
            raw_x_max = max(raw_x_max, float(np.max(t_curve[0])))
            raw_y_max = max(raw_y_max, float(np.max(t_curve[1])))
        if v_curve is not None:
            raw_x_max = max(raw_x_max, float(np.max(v_curve[0])))
            raw_y_max = max(raw_y_max, float(np.max(v_curve[1])))
        items.append((m, t_curve, v_curve))

    fr = _plot_frame(q_req, p_req, raw_x_max, raw_y_max, width, height,
                     right_pad=380)
    d, px = fr["d"], fr["px"]
    font_s = fr["font_s"]
    ml, mt, plot_w, plot_h = fr["ml"], fr["mt"], fr["plot_w"], fr["plot_h"]
    x_max = fr["x_max"]

    legend = []
    for idx, (m, t_curve, v_curve) in enumerate(items):
        color = _COMPARE_COLORS[idx % len(_COMPARE_COLORS)]
        if t_curve is not None:
            pts = [px(float(a), float(b)) for a, b in zip(*t_curve)]
            d.line(pts, fill=color, width=2)
            legend.append((color, "solid", "%s (дроссель)" % m))
        if v_curve is not None:
            mask = v_curve[0] <= x_max
            q_c, p_c = v_curve[0][mask], v_curve[1][mask]
            if len(q_c) >= 2:
                pts = [px(float(a), float(b)) for a, b in zip(q_c, p_c)]
                _dashed_line(d, pts, fill=color, dash=5, width=2)
                legend.append((color, "dash", "%s (ЧРП)" % m))

    _draw_working_point(d, px, q_req, p_req, ml, mt, plot_h)

    # легенда в правой панели: пары идут последовательно, у обеих кривых
    # одного вентилятора — один цвет и одна толщина
    if legend:
        lx = ml + plot_w + 18
        ly = mt + 2
        row_h = 17
        for color, style, label in legend:
            if ly + row_h > height - 24:
                break
            if style == "solid":
                d.line([(lx, ly + 6), (lx + 22, ly + 6)], fill=color, width=2)
            else:
                _dash_swatch(d, lx, lx + 22, ly + 6, color, width=2)
            d.text((lx + 28, ly - 2), label[:56], fill=(30, 30, 30), font=font_s)
            ly += row_h

    return _png(fr["img"])


def compare_chart_base64(throttle_results: List[dict],
                         vfd_results: List[dict],
                         req: dict) -> str:
    """PNG общего графика сравнения → base64."""
    return base64.b64encode(
        render_compare_chart(throttle_results, vfd_results, req)
    ).decode("ascii")
