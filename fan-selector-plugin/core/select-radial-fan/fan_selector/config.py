"""Конфигурация программы.

Централизованное хранилище всех настроек приложения:
- Физические константы (плотность воздуха)
- Параметры аппроксимации (степень полинома, мин. точек)
- Таблица запасов мощности двигателя
- Границы валидации входных данных
- Пути к данным (с поддержкой переменных окружения)

Конфигурация загружается из внешнего JSON-файла data/config.json.
При отсутствии файла используются значения по умолчанию (с предупреждением);
при неполных данных или некорректных значениях приложение не запускается
(fail-fast).

================================================================
ОГЛАВЛЕНИЕ (для chunked reading — ищите символ через gh_search)
================================================================

Секция                        | Символ               | Описание
------------------------------|----------------------|----------------------------------
ИСКЛЮЧЕНИЯ                    | ConfigError          | Ошибка конфигурации (fail-fast)
ГРАНИЦЫ ВАЛИДАЦИИ             | ValidationLimits     | Диапазоны входных параметров
ОСНОВНАЯ КОНФИГУРАЦИЯ         | Config               | Главный объект настроек
  └─ data_dir (property)      | Config.data_dir      | Путь к данным (env FAN_DATA_DIR)
ЗАГРУЗКА ИЗ JSON              |                      |
  └─ Константы                | REQUIRED_FIELDS      | Обязательные поля config.json
  └─ Константы                | VALIDATION_FIELDS    | Поля секции validation
  └─ Значения по умолчанию    | _DEFAULT_CONFIG      | Дефолты без config.json
  └─ _default_config_path()   | _default_config_path | Путь рядом с пакетом
  └─ _resolve_config_path()   | _resolve_config_path | Путь к файлу (env > default)
  └─ _load_config_json()      | _load_config_json    | Чтение JSON (или дефолты)
  └─ _check_type()            | _check_type          | Проверка типа поля
  └─ _validate_config()       | _validate_config     | Полная валидация данных
  └─ _parse_safety_table()    | _parse_safety_table  | Парсинг таблицы запасов
  └─ load_config()            | load_config          | Публичная точка входа

Как читать этот файл по частям:
  1. Прочтите строки 1-45 (этот docstring + импорты + ConfigError)
  2. Для конкретного символа — gh_search с именем символа
  3. Для обзора валидации — ищите _validate_config
  4. Для обзора загрузки — ищите load_config
  5. Для данных Config — ищите class Config
================================================================
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple
import copy
import json
import os
import warnings


# =========================================================
# ИСКЛЮЧЕНИЯ
# =========================================================

class ConfigError(Exception):
    """Критическая ошибка конфигурации.

    Выбрасывается при отсутствии файла, неполных данных
    или некорректных значениях. Приложение не может
    продолжить работу.
    """


# =========================================================
# ГРАНИЦЫ ВАЛИДАЦИИ ВХОДНЫХ ДАННЫХ
# =========================================================

@dataclass
class ValidationLimits:
    """Допустимые диапазоны входных параметров подбора.

    Attributes:
        q_min: Минимальный расход воздуха, м³/ч
        q_max: Максимальный расход воздуха, м³/ч
        p_min: Минимальное давление, Па
        p_max: Максимальное давление, Па
    """
    q_min: float
    q_max: float
    p_min: float
    p_max: float


@dataclass
class VfdConfig:
    """Параметры частотного регулирования (ЧРП/VFD).

    Attributes:
        f_nom_hz: Номинальная частота сети, Гц
        f_min_hz_default: Минимальная частота по умолчанию, Гц
        f_max_hz_default: Максимальная частота по умолчанию, Гц
        eta_vfd: КПД частотного преобразователя (0..1)
        eta_motor_part_load: КПД двигателя при частичной нагрузке (0..1)
    """
    f_nom_hz: float = 50.0
    f_min_hz_default: float = 20.0
    f_max_hz_default: float = 60.0
    eta_vfd: float = 0.97
    eta_motor_part_load: float = 0.85


# =========================================================
# ОСНОВНАЯ КОНФИГУРАЦИЯ
# =========================================================

@dataclass
class Config:
    """Главный объект конфигурации приложения.

    Содержит все настройки: физические константы, параметры расчёта,
    границы валидации, пути к данным. Загружается из JSON-файла.

    Attributes:
        rho_air: Плотность воздуха, кг/м³
        poly_degree: Степень полинома для МНК-аппроксимации
        min_points_for_degree: Минимальное количество точек для заданной степени
        safety_table: Таблица запасов мощности ((max_kw, factor), ...)
        default_d_reg_max_pa: Макс. дорегулирование по умолчанию, Па
        default_q_display: Расход для отображения графика, м³/ч
        top_n: Максимальное количество результатов в выдаче
        validation: Границы валидации входных данных
    """
    rho_air: float
    poly_degree: int
    min_points_for_degree: int
    safety_table: Tuple[Tuple[float, float], ...]
    default_d_reg_max_pa: float
    default_q_display: float
    top_n: int
    validation: ValidationLimits
    vfd: VfdConfig = field(default_factory=VfdConfig)

    @property
    def data_dir(self) -> str:
        """Директория с данными (fans.json, motors.json и т.д.).

        Может быть переопределена через переменную окружения FAN_DATA_DIR.
        По умолчанию — папка data/ рядом с кодом.
        """
        env_dir = os.environ.get("FAN_DATA_DIR")
        if env_dir:
            return env_dir
        # Для PyInstaller: _MEIPASS — временная папка распаковки
        base = getattr(os.sys, '_MEIPASS', os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(base, "data")


# =========================================================
# ЗАГРУЗКА КОНФИГУРАЦИИ ИЗ JSON
# =========================================================

# Обязательные поля корневого уровня
REQUIRED_FIELDS = [
    "rho_air", "poly_degree", "min_points_for_degree",
    "default_d_reg_max_pa", "default_q_display",
    "top_n", "validation", "safety_table",
]

# Обязательные поля секции validation
VALIDATION_FIELDS = [
    "q_min", "q_max", "p_min", "p_max",
]

# Значения по умолчанию: используются, если data/config.json отсутствует.
# Должны совпадать с поставляемым файлом data/config.json и полностью
# проходить _validate_config().
_DEFAULT_CONFIG = {
    "rho_air": 1.2,
    "poly_degree": 6,
    "min_points_for_degree": 7,
    "default_d_reg_max_pa": 1500.0,
    "default_q_display": 7500.0,
    "top_n": 10,
    "validation": {
        "q_min": 100.0,
        "q_max": 100000.0,
        "p_min": 10.0,
        "p_max": 10000.0,
    },
    "safety_table": [
        {"max_power_kw": 0.5, "factor": 1.50},
        {"max_power_kw": 1.0, "factor": 1.30},
        {"max_power_kw": 2.0, "factor": 1.20},
        {"max_power_kw": 5.0, "factor": 1.15},
        {"max_power_kw": None, "factor": 1.10},
    ],
    "vfd": {
        "f_nom_hz": 50.0,
        "f_min_hz_default": 20.0,
        "f_max_hz_default": 60.0,
        "eta_vfd": 0.97,
        "eta_motor_part_load": 0.85,
    },
}


def _default_config_path() -> str:
    """Путь к config.json по умолчанию — относительно кода пакета.

    Работает одинаково из репозитория, из установленного wheel и из раскладки
    плагина DSH: ``data/`` лежит рядом с каталогом ``fan_selector/``.
    """
    return str(Path(__file__).resolve().parents[1] / "data" / "config.json")


def _resolve_config_path() -> str:
    """Определяет путь к файлу конфигурации.

    Приоритет:
    1. Переменная окружения FAN_CONFIG_PATH
    2. Путь PyInstaller (_MEIPASS), если файл там действительно есть
    3. Путь по умолчанию рядом с пакетом (data/config.json)

    Возвращает первый существующий путь; если не существует ни один —
    путь по умолчанию (чтобы сообщение об ошибке было осмысленным).
    """
    env_path = os.environ.get("FAN_CONFIG_PATH")
    if env_path:
        return env_path

    candidates = []

    # Для PyInstaller: _MEIPASS — временная папка распаковки
    meipass = getattr(os.sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, "data", "config.json"))

    default_path = _default_config_path()
    candidates.append(default_path)

    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return default_path


def _load_config_json(path: str) -> dict:
    """Читает и парсит JSON-файл конфигурации.

    Args:
        path: Путь к файлу config.json

    Returns:
        Распарсенный словарь с данными конфигурации. Если файла нет —
        значения по умолчанию (_DEFAULT_CONFIG) и предупреждение.

    Raises:
        ConfigError: Если файл существует, но содержит невалидный JSON
    """
    if not os.path.exists(path):
        warnings.warn(
            f"Файл конфигурации не найден: {path}. "
            f"Используются значения по умолчанию.",
            stacklevel=2,
        )
        return copy.deepcopy(_DEFAULT_CONFIG)

    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Ошибка парсинга {path}: {e}")


def _check_type(data: dict, field: str, expected: tuple, section: str = "") -> None:
    """Проверяет тип значения поля.

    Args:
        data: Словарь с данными
        field: Имя проверяемого поля
        expected: Кортеж допустимых типов
        section: Имя секции (для validation-полей)

    Raises:
        ConfigError: Если тип не соответствует ожидаемому
    """
    value = data[field]
    # bool — подкласс int в Python, исключаем его
    if isinstance(value, bool) or not isinstance(value, expected):
        prefix = f"{section}." if section else ""
        expected_names = ", ".join(t.__name__ for t in expected)
        raise ConfigError(
            f"Поле '{prefix}{field}' должно быть типа "
            f"{expected_names}, получено: {type(value).__name__} ({value!r})"
        )


def _validate_config(data: dict) -> None:
    """Проверяет полноту и корректность данных конфигурации.

    Выполняет три уровня проверки:
    1. Наличие всех обязательных полей
    2. Соответствие типов
    3. Допустимость диапазонов значений

    Raises:
        ConfigError: При любом нарушении
    """
    # --- 1. Проверка наличия всех полей ---
    for field_name in REQUIRED_FIELDS:
        if field_name not in data:
            raise ConfigError(
                f"Обязательное поле '{field_name}' отсутствует в config.json"
            )

    if not isinstance(data["validation"], dict):
        raise ConfigError("Поле 'validation' должно быть объектом")

    for field_name in VALIDATION_FIELDS:
        if field_name not in data["validation"]:
            raise ConfigError(
                f"Обязательное поле 'validation.{field_name}' "
                f"отсутствует в config.json"
            )

    # --- 2. Проверка типов (корневой уровень) ---
    _check_type(data, "rho_air", (int, float))
    _check_type(data, "poly_degree", (int,))
    _check_type(data, "min_points_for_degree", (int,))
    _check_type(data, "default_d_reg_max_pa", (int, float))
    _check_type(data, "default_q_display", (int, float))
    _check_type(data, "top_n", (int,))

    # --- 3. Проверка диапазонов (корневой уровень) ---
    if data["rho_air"] <= 0:
        raise ConfigError(
            f"Поле 'rho_air' должно быть > 0, получено {data['rho_air']}"
        )
    if not (2 <= data["poly_degree"] <= 10):
        raise ConfigError(
            f"Поле 'poly_degree' должно быть от 2 до 10, "
            f"получено {data['poly_degree']}"
        )
    if data["min_points_for_degree"] < 2:
        raise ConfigError(
            f"Поле 'min_points_for_degree' должно быть >= 2, "
            f"получено {data['min_points_for_degree']}"
        )
    if data["default_d_reg_max_pa"] < 0:
        raise ConfigError(
            f"Поле 'default_d_reg_max_pa' должно быть >= 0, "
            f"получено {data['default_d_reg_max_pa']}"
        )
    if data["default_q_display"] <= 0:
        raise ConfigError(
            f"Поле 'default_q_display' должно быть > 0, "
            f"получено {data['default_q_display']}"
        )
    if data["top_n"] < 1:
        raise ConfigError(
            f"Поле 'top_n' должно быть >= 1, получено {data['top_n']}"
        )

    # --- 4. Проверка типов (validation) ---
    val = data["validation"]
    for field_name in VALIDATION_FIELDS:
        _check_type(val, field_name, (int, float), section="validation")

    # --- 5. Проверка диапазонов (validation) ---
    if val["q_min"] < 0:
        raise ConfigError(
            f"Поле 'validation.q_min' должно быть >= 0, получено {val['q_min']}"
        )
    if val["q_max"] <= val["q_min"]:
        raise ConfigError(
            f"Поле 'validation.q_min' ({val['q_min']}) должно быть < "
            f"validation.q_max ({val['q_max']})"
        )
    if val["p_min"] < 0:
        raise ConfigError(
            f"Поле 'validation.p_min' должно быть >= 0, получено {val['p_min']}"
        )
    if val["p_max"] <= val["p_min"]:
        raise ConfigError(
            f"Поле 'validation.p_min' ({val['p_min']}) должно быть < "
            f"validation.p_max ({val['p_max']})"
        )


def _parse_safety_table(entries: list) -> Tuple[Tuple[float, float], ...]:
    """Парсит и валидирует таблицу запасов мощности из JSON.

    Преобразует массив объектов JSON во внутренний формат
    Tuple[Tuple[float, float], ...], где:
    - первый элемент пары — верхняя граница мощности (кВт)
    - второй элемент — коэффициент запаса

    `null` в max_power_kw преобразуется в float("inf").

    Args:
        entries: Массив словарей из config.json

    Returns:
        Кортеж пар (max_power_kw, factor) для использования в core.py

    Raises:
        ConfigError: При любом нарушении структуры или логики
    """
    if not isinstance(entries, list):
        raise ConfigError("Поле 'safety_table' должно быть массивом")

    if len(entries) == 0:
        raise ConfigError(
            "Таблица 'safety_table' не должна быть пустой (минимум 1 запись)"
        )

    result = []
    null_count = 0
    prev_max = -1.0

    for i, entry in enumerate(entries):
        # --- Проверка структуры ---
        if not isinstance(entry, dict):
            raise ConfigError(
                f"Запись #{i} в 'safety_table' должна быть объектом"
            )
        if "max_power_kw" not in entry or "factor" not in entry:
            raise ConfigError(
                f"Запись #{i} в 'safety_table' должна содержать "
                f"поля 'max_power_kw' и 'factor'"
            )

        max_kw = entry["max_power_kw"]
        factor = entry["factor"]

        # --- Проверка factor ---
        if isinstance(factor, bool) or not isinstance(factor, (int, float)):
            raise ConfigError(
                f"Запись #{i} в 'safety_table': "
                f"'factor' должен быть числом, получено: {factor!r}"
            )
        if factor <= 1.0:
            raise ConfigError(
                f"Запись #{i} в 'safety_table': "
                f"коэффициент запаса ({factor}) должен быть > 1.0"
            )

        # --- Проверка max_power_kw ---
        if max_kw is None:
            # null → float("inf"), должна быть только последняя
            null_count += 1
            if null_count > 1:
                raise ConfigError(
                    f"В 'safety_table' должна быть ровно одна запись "
                    f"с 'max_power_kw: null' — в конце таблицы"
                )
            if i != len(entries) - 1:
                raise ConfigError(
                    f"Запись с 'max_power_kw: null' в 'safety_table' "
                    f"должна быть последней (найдена на позиции #{i})"
                )
            result.append((float("inf"), float(factor)))
        else:
            if isinstance(max_kw, bool) or not isinstance(max_kw, (int, float)):
                raise ConfigError(
                    f"Запись #{i} в 'safety_table': "
                    f"'max_power_kw' должен быть числом или null, "
                    f"получено: {max_kw!r}"
                )
            if max_kw <= 0:
                raise ConfigError(
                    f"Запись #{i} в 'safety_table': "
                    f"мощность ({max_kw}) должна быть > 0"
                )
            if max_kw <= prev_max:
                raise ConfigError(
                    f"Записи в 'safety_table' должны быть отсортированы "
                    f"по возрастанию 'max_power_kw'. "
                    f"Запись #{i - 1} ({prev_max}) >= запись #{i} ({max_kw})"
                )
            prev_max = max_kw
            result.append((float(max_kw), float(factor)))

    # --- Проверка: есть ли catch-all запись ---
    if null_count == 0:
        raise ConfigError(
            "В 'safety_table' должна быть запись с 'max_power_kw: null' "
            "(catch-all для мощностей выше максимального порога)"
        )

    return tuple(result)


def load_config() -> Config:
    """Загружает конфигурацию из JSON-файла.

    Публичная точка входа: находит файл, читает, валидирует
    и создаёт объект Config.

    Returns:
        Полностью валидный объект Config

    Raises:
        ConfigError: При любой ошибке загрузки или валидации
    """
    path = _resolve_config_path()
    data = _load_config_json(path)
    _validate_config(data)

    safety_table = _parse_safety_table(data["safety_table"])

    # Блок vfd — опциональный (обратная совместимость с config без ЧРП)
    vfd_raw = data.get("vfd") or {}
    vfd = VfdConfig(
        f_nom_hz=float(vfd_raw.get("f_nom_hz", 50.0)),
        f_min_hz_default=float(vfd_raw.get("f_min_hz_default", 20.0)),
        f_max_hz_default=float(vfd_raw.get("f_max_hz_default", 60.0)),
        eta_vfd=float(vfd_raw.get("eta_vfd", 0.97)),
        eta_motor_part_load=float(vfd_raw.get("eta_motor_part_load", 0.85)),
    )

    return Config(
        rho_air=float(data["rho_air"]),
        poly_degree=int(data["poly_degree"]),
        min_points_for_degree=int(data["min_points_for_degree"]),
        safety_table=safety_table,
        default_d_reg_max_pa=float(data["default_d_reg_max_pa"]),
        default_q_display=float(data["default_q_display"]),
        top_n=int(data["top_n"]),
        validation=ValidationLimits(
            q_min=float(data["validation"]["q_min"]),
            q_max=float(data["validation"]["q_max"]),
            p_min=float(data["validation"]["p_min"]),
            p_max=float(data["validation"]["p_max"]),
        ),
        vfd=vfd,
    )
