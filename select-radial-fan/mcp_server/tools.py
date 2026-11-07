"""Чистые функции инструментов MCP (без зависимости от SDK `mcp`).

Вынесены из server.py, чтобы логику адаптера можно было тестировать без установки
SDK MCP (см. tests/test_mcp.py). server.py лишь регистрирует эти функции как
инструменты/ресурсы MCP.
"""
from __future__ import annotations

import os
from typing import Literal

from fan_selector.repositories import DATA_DIR
from fan_selector.select import run_selection, catalog_lookup, chart_selection


def select_fan(
    q_req: float,
    p_req: float,
    pressure_type: Literal["FULL", "STATIC"] = "FULL",
    d_reg_max: float = 1500.0,
    t_air: float = 20.0,
    series: list[str] | None = None,
    sizes: list[float] | None = None,
    rpms: list[int] | None = None,
    regulation_mode: Literal["THROTTLE", "VFD"] = "THROTTLE",
    freq_min_hz: float = 20.0,
    freq_max_hz: float = 60.0,
) -> dict:
    """Подобрать радиальный вентилятор (ВР 86-77 / ВР 280-46) по расходу и давлению.

    `regulation_mode`: THROTTLE — дроссельное регулирование (по умолчанию);
    VFD — частотное регулирование с подбором частотного преобразователя.
    Для VFD задаётся диапазон частоты `freq_min_hz`/`freq_max_hz` (Гц).

    Возвращает `fan-result/v1`: сводку (`summary`) и список `results[]`.
    """
    return run_selection({
        "q_req": q_req,
        "p_req": p_req,
        "pressure_type": pressure_type,
        "d_reg_max": d_reg_max,
        "t_air": t_air,
        "series": series or [],
        "sizes": sizes or [],
        "rpms": rpms or [],
        "regulation_mode": regulation_mode,
        "freq_min_hz": freq_min_hz,
        "freq_max_hz": freq_max_hz,
    })


def lookup_catalog(
    series: list[str] | None = None,
    dn: float | None = None,
    d_over_dn: float | None = None,
) -> dict:
    """Каталожные карточки (габариты, масса, шум, исполнения, двигатели).

    Возвращает `fan-catalog/v1` — список `items[]`.
    """
    return catalog_lookup({
        "series": series,
        "dn": dn,
        "d_over_dn": d_over_dn,
    })


def fan_chart(
    q_req: float,
    p_req: float,
    pressure_type: Literal["FULL", "STATIC"] = "FULL",
) -> dict:
    """PNG-график характеристик P(Q) и рабочей точки.

    Возвращает `fan-chart/v1` с полем `chart_png_base64`.
    """
    return chart_selection({
        "q_req": q_req,
        "p_req": p_req,
        "pressure_type": pressure_type,
    })


def read_data(name: str) -> str:
    """Прочитать файл справочника из data/ (utf-8-sig — снимает BOM, если есть)."""
    with open(os.path.join(DATA_DIR, name), encoding="utf-8-sig") as f:
        return f.read()


def data_fans() -> str:
    """Справочник вентиляторов (fans.json)."""
    return read_data("fans.json")


def data_impellers() -> str:
    """Справочник рабочих колёс и кривых (impellers.json)."""
    return read_data("impellers.json")


def data_motors() -> str:
    """Справочник электродвигателей (motors.json)."""
    return read_data("motors.json")


def data_catalog() -> str:
    """Каталожные карточки массо-габаритов и исполнений (catalog.json)."""
    return read_data("catalog.json")


def data_config() -> str:
    """Конфигурация расчёта (config.json)."""
    return read_data("config.json")
