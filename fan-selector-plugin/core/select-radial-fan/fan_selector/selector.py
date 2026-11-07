"""Оркестратор подбора."""
from typing import List, Sequence

from .config import Config
from .core import compute_one
from .models import Fan, FanResult, Motor, SelectionRequest, Vfd
from .vfd import compute_vfd_one


def passes_filters(fan: Fan, req: SelectionRequest) -> bool:
    """Проверяет, подходит ли вентилятор под фильтры запроса.
    
    Args:
        fan: Вентилятор для проверки
        req: Запрос с фильтрами (серии, размеры, обороты)
    
    Returns:
        True если вентилятор проходит фильтры, False иначе
    """
    if not fan.active:
        return False
    if req.series and fan.series not in req.series:
        return False
    if req.sizes and fan.size not in req.sizes:
        return False
    if req.rpms and fan.max_n not in req.rpms:
        return False
    return True


def select_fans(fans: Sequence[Fan],
                motors: Sequence[Motor],
                req: SelectionRequest,
                cfg: Config) -> List[FanResult]:
    """Выполняет подбор вентиляторов по заданным параметрам.
    
    Проходит по всем вентиляторам, применяет фильтры и вычисляет
    параметры для каждого подходящего вентилятора. Возвращает
    отсортированный список результатов (сначала прошедшие отбор,
    затем по минимальному дорегулированию).
    
    Args:
        fans: Список всех вентиляторов из БД
        motors: Список всех электродвигателей из БД
        req: Запрос с параметрами подбора
        cfg: Конфигурация (обязательный параметр)
    
    Returns:
        Список результатов подбора (максимум top_n штук)
    """
    results: List[FanResult] = []
    for fan in fans:
        if not passes_filters(fan, req):
            continue
        r = compute_one(fan, req, motors, cfg)
        results.append(r)

    # Сортировка: сначала прошедшие отбор, затем по дорегулированию
    results.sort(key=lambda r: (not r.passed, r.d_reg_pa))
    return results[:cfg.top_n]


def select_fans_vfd(fans: Sequence[Fan],
                    motors: Sequence[Motor],
                    vfds: Sequence[Vfd],
                    req: SelectionRequest,
                    cfg: Config) -> List[FanResult]:
    """Подбор вентиляторов в режиме частотного регулирования (ЧРП).

    Аналогичен select_fans, но для каждого вентилятора выполняет расчёт по
    законам подобия (vfd.compute_vfd_one) и подбирает частотный преобразователь.
    Сортировка — сначала прошедшие, затем по возрастанию требуемой частоты.
    """
    results: List[FanResult] = []
    for fan in fans:
        if not passes_filters(fan, req):
            continue
        r = compute_vfd_one(fan, req, motors, vfds, cfg)
        results.append(r)

    results.sort(key=lambda r: (not r.passed, r.f_hz if r.f_hz is not None else float("inf")))
    return results[:cfg.top_n]
