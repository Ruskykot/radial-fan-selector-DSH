"""
fan_selector — ядро подбора радиальных вентиляторов.

Содержит чистое расчётное ядро (без I/O интерфейсов) и универсальный
адаптер JSON-in/JSON-out. Ввод-вывод и визуализацию берёт на себя
внешний рантайм (DeepSeek Harness через навык .dsh/skills/fan-selector).

Модули:
- config: конфигурация и валидация
- models: доменные модели (Fan, Impeller, Motor, SelectionRequest, FanResult)
- repositories: загрузка данных из JSON
- core: расчётное ядро (чистые функции, НЕ менять)
- selector: оркестратор подбора
- select: универсальный адаптер run_selection(dict) -> dict
"""

__version__ = "2.4.0"

from .models import (
    Fan,
    Impeller,
    Motor,
    Vfd,
    SelectionRequest,
    FanResult,
    PressureType,
    RegulationMode,
    ResultStatus,
)
from .config import Config
from .selector import select_fans, select_fans_vfd
from .repositories import load_all, load_fans, load_motors, load_catalog, load_vfds
from .select import run_selection, run_comparison, catalog_lookup, chart_selection

__all__ = [
    "Fan",
    "Impeller",
    "Motor",
    "Vfd",
    "SelectionRequest",
    "FanResult",
    "PressureType",
    "RegulationMode",
    "ResultStatus",
    "Config",
    "select_fans",
    "select_fans_vfd",
    "load_all",
    "load_fans",
    "load_motors",
    "load_vfds",
    "load_catalog",
    "run_selection",
    "run_comparison",
    "catalog_lookup",
    "chart_selection",
]
