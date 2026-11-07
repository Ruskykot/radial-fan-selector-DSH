"""
Модуль репозиториев для загрузки данных из JSON-файлов.

Этот модуль отвечает за:
- Загрузку данных о вентиляторах из fans.json
- Загрузку данных о рабочих колёсах из impellers.json
- Загрузку данных о электродвигателях из motors.json
- Кэширование загруженных данных для повышения производительности
- Валидацию и преобразование данных в доменные модели

Все функции загрузки используют lru_cache для кэширования результатов,
что позволяет избежать повторного чтения файлов при каждом вызове.

Типичное использование:
    from fan_selector.repositories import load_all
    fans, motors = load_all()
"""

from __future__ import annotations
import json
import os
from functools import lru_cache
from typing import Dict, List, Tuple

from .models import Fan, Impeller, Motor, CatalogSize, Vfd


# Путь к папке data/ с JSON-файлами вентиляторов.
# Порядок разрешения:
#   1) переменная окружения FAN_DATA_DIR — явное переопределение;
#   2) fan_selector/data/ — установленный пакет (wheel; копируется build-хуком setup.py);
#   3) data/ рядом с пакетом (на уровень выше fan_selector/) — запуск из репозитория.
_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
_PACKAGE_DATA_DIR = os.path.join(_PACKAGE_DIR, "data")
_SIBLING_DATA_DIR = os.path.join(os.path.dirname(_PACKAGE_DIR), "data")

DATA_DIR = os.environ.get(
    "FAN_DATA_DIR",
    _PACKAGE_DATA_DIR if os.path.isdir(_PACKAGE_DATA_DIR) else _SIBLING_DATA_DIR,
)


def _load_json(filename: str) -> list:
    """
    Загрузить JSON-файл из папки data/.
    
    Использует кодировку utf-8-sig для автоматического удаления
    BOM (Byte Order Mark), если файл был сохранён в UTF-8 с BOM.
    
    Args:
        filename: Имя файла (например, "fans.json")
        
    Returns:
        Распарсенные данные из JSON
        
    Raises:
        FileNotFoundError: Если файл не найден
    """
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Файл не найден: {path}")
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_impellers() -> Dict[str, Impeller]:
    """
    Загрузить данные о рабочих колёсах из impellers.json.
    
    Результат кэшируется с помощью lru_cache для повышения производительности.
    
    Returns:
        Словарь {id_колеса: Impeller}
    """
    data = _load_json("impellers.json")
    return {item["id"]: Impeller(**item) for item in data}


@lru_cache(maxsize=1)
def load_fans() -> List[Fan]:
    """
    Загрузить данные о вентиляторах из fans.json.
    
    Результат кэшируется с помощью lru_cache для повышения производительности.
    
    Returns:
        Список объектов Fan
    """
    data = _load_json("fans.json")
    impellers = load_impellers()
    fans = []
    for item in data:
        fan = Fan(**item)
        if fan.impeller_id in impellers:
            fan.impeller = impellers[fan.impeller_id]
        fans.append(fan)
    return fans


@lru_cache(maxsize=1)
def load_motors() -> List[Motor]:
    """
    Загрузить данные о электродвигателях из motors.json.
    
    Результат кэшируется с помощью lru_cache для повышения производительности.
    
    Returns:
        Список объектов Motor
    """
    data = _load_json("motors.json")
    return [Motor(**item) for item in data]


@lru_cache(maxsize=1)
def load_vfds() -> List[Vfd]:
    """
    Загрузить справочник частотных преобразователей из vfd.json.

    Результат кэшируется с помощью lru_cache. Если файла нет — пустой список
    (режим VFD вернёт статус VFD_NOT_FOUND, не бросая исключений).

    Returns:
        Список объектов Vfd
    """
    try:
        data = _load_json("vfd.json")
    except FileNotFoundError:
        return []
    return [Vfd(**item) for item in data]


@lru_cache(maxsize=1)
def load_catalog() -> List[CatalogSize]:
    """
    Загрузить каталог типоразмеров из catalog.json.

    Каталог описывает типоразмеры как (series, dn, d_over_dn) с геометрией,
    массой, шумом и списком доступных двигателей.

    Returns:
        Список объектов CatalogSize
    """
    try:
        data = _load_json("catalog.json")
    except FileNotFoundError:
        return []
    sizes = []
    for item in data:
        item = {k: v for k, v in item.items() if k != "type"}
        sizes.append(CatalogSize(**item))
    return sizes


def load_all() -> Tuple[List[Fan], List[Motor]]:
    """
    Загрузить все данные (вентиляторы и двигатели).
    
    Удобная функция для загрузки всех необходимых данных одним вызовом.
    
    Returns:
        Кортеж (fans, motors)
    """
    return load_fans(), load_motors()


def clear_cache() -> None:
    """
    Очистить кэш загруженных данных.
    
    Полезно при тестировании или если данные в JSON-файлах изменились.
    """
    load_impellers.cache_clear()
    load_fans.cache_clear()
    load_motors.cache_clear()
    load_vfds.cache_clear()
    load_catalog.cache_clear()
