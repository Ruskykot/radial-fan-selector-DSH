"""Доменные модели."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np


class PressureType(str, Enum):
    """Тип давления для расчёта."""
    FULL = "Полное"
    STATIC = "Статическое"


class RegulationMode(str, Enum):
    """Режим регулирования."""
    THROTTLE = "THROTTLE"  # дроссельный (по умолчанию)
    VFD = "VFD"            # частотное регулирование (ЧРП)


class ResultStatus(str, Enum):
    """Статус результата подбора вентилятора."""
    OK = "OK"
    OUT_OF_FLOW_RANGE = "ВНЕ ДИАПАЗОНА ПО РАСХОДУ"
    INSUFFICIENT_POINTS = "НЕДОСТАТОЧНО ТОЧЕК"
    CURVE_BELOW_POINT = "КРИВАЯ НИЖЕ ТОЧКИ"
    OVER_DOR_REG = "ПРЕВЫШЕНИЕ ДОРЕГ"
    NO_EFFICIENCY_DATA = "НЕТ ДАННЫХ КПД"
    MOTOR_NOT_FOUND = "ДВИГАТЕЛЬ НЕ ПОДОБРАН"
    FREQ_BELOW_MIN = "FREQ_BELOW_MIN"
    FREQ_ABOVE_MAX = "FREQ_ABOVE_MAX"
    NO_NETWORK_INTERSECTION = "NO_NETWORK_INTERSECTION"
    VFD_NOT_FOUND = "VFD_NOT_FOUND"


@dataclass
class Impeller:
    """Рабочее колесо (справочник).

    Хранит геометрические и аэродинамические параметры рабочего колеса,
    загружаемые из impellers.json. Используется для расчёта характеристик
    вентилятора.
    """
    id: str               # Уникальный идентификатор (например, "wr86_77_2_5")
    series: str           # Серия вентилятора (например, "ВР 86-77")
    diameter: float       # Диаметр рабочего колеса, м
    nominal: str = "DN"   # Номинальный размер (DN250, DN315 и т.д.)
    area_f_m2: float = 0.0            # Площадь выходного сечения, м²
    q_min: float = 0.0               # Минимальный расход, м³/ч
    q_max: float = 0.0               # Максимальный расход, м³/ч
    q_points: List[float] = field(default_factory=list)   # Точки расхода для Q-P характеристики
    p_points: List[float] = field(default_factory=list)   # Точки полного давления, Па
    q_eff: List[float] = field(default_factory=list)      # Точки расхода для Q-η характеристики
    eff_points: List[float] = field(default_factory=list)  # Точки КПД (0..1)


@dataclass
class Fan:
    """Карточка вентилятора.

    Основная модель вентилятора, загружаемая из fans.json. Содержит
    идентификационные данные, ограничения по двигателю, шумовые характеристики
    и ссылку на рабочее колесо (заполняется при загрузке).
    """
    type: str               # Тип вентилятора (например, "Радиальный")
    series: str             # Серия (например, "ВР 86-77")
    model: str              # Полная модель (например, "ВР 86-77-4-DN-1500")
    max_n: int              # Максимальная частота вращения, об/мин
    impeller_id: str        # ID рабочего колеса из impellers.json
    dn: Optional[float] = None        # Номинальный диаметр DN (типоразмер)
    d_over_dn: Optional[float] = None # Отношение D/DN (подрезка колеса)
    motor_type: str = "АС"  # Тип двигателя (АС — асинхронный)
    voltage: str = "380/50" # Напряжение питания
    min_n_kw: float = 0.0   # Минимальная мощность двигателя, кВт
    max_n_kw: float = 9999.0  # Максимальная мощность двигателя, кВт
    mass: float = 0.0       # Масса вентилятора, кг
    connection_type: str = "Фланцевое"  # Тип соединения
    dims: dict = field(default_factory=dict)  # Габаритные размеры
    noise_body: List[float] = field(default_factory=list)  # Шум корпуса, дБ(А)
    noise_in: List[float] = field(default_factory=list)    # Шум на входе, дБ(А)
    noise_out: List[float] = field(default_factory=list)   # Шум на выходе, дБ(А)
    active: bool = True     # Вентилятор активен (доступен для подбора)
    impeller: Optional[Impeller] = field(default=None, repr=False)  # Ссылка на рабочее колесо

    # --- Кэшируемые аппроксимации характеристик ---
    # Заполняются при первом обращении, чтобы не пересчитывать полиномы
    # при каждом вызове compute_one(). Тип np.poly1d — полином numpy.
    poly_work: Optional[np.poly1d] = None   # Рабочая характеристика (P от Q) для заданного давления типа
    poly_full: Optional[np.poly1d] = None   # Полная характеристика (P от Q)

    # Прокси-свойства для совместимости с ядром
    @property
    def size(self) -> float:
        """Диаметр рабочего колеса (прокси к impeller.diameter)."""
        return self.impeller.diameter if self.impeller else 0.0

    @property
    def q_min(self) -> float:
        """Минимальный расход (прокси к impeller.q_min)."""
        return self.impeller.q_min if self.impeller else 0.0

    @property
    def q_max(self) -> float:
        """Максимальный расход (прокси к impeller.q_max)."""
        return self.impeller.q_max if self.impeller else 0.0

    @property
    def area_f_m2(self) -> float:
        """Площадь выходного сечения (прокси к impeller.area_f_m2)."""
        return self.impeller.area_f_m2 if self.impeller else 0.0

    @property
    def q_points(self) -> List[float]:
        """Точки расхода (прокси к impeller.q_points)."""
        return self.impeller.q_points if self.impeller else []

    @property
    def p_points(self) -> List[float]:
        """Точки полного давления (прокси к impeller.p_points)."""
        return self.impeller.p_points if self.impeller else []

    @property
    def q_eff(self) -> List[float]:
        """Точки расхода для КПД (прокси к impeller.q_eff)."""
        return self.impeller.q_eff if self.impeller else []

    @property
    def eff_points(self) -> List[float]:
        """Точки КПД (прокси к impeller.eff_points)."""
        return self.impeller.eff_points if self.impeller else []


@dataclass
class Motor:
    """Электродвигатель.

    Модель электродвигателя, загружаемая из motors.json.
    Содержит параметры для подбора двигателя к вентилятору.
    """
    name: str          # Название (например, "АИР80В4")
    n_rpm: int         # Частота вращения, об/мин
    n_kw: float        # Мощность, кВт
    i_nom: Optional[float] = None       # Номинальный ток, А (справочное)
    mass: Optional[float] = None        # Масса, кг (справочное)
    i_start: Optional[float] = None     # Пусковой ток, А (справочное)
    m_max_m_nom: Optional[float] = None # Кратность максимального момента (M_max/M_nom) (справочное)
    m_start_m_nom: Optional[float] = None  # Кратность пускового момента (M_start/M_nom) (справочное)


@dataclass
class Vfd:
    """Частотный преобразователь (ЧРП), загружаемый из vfd.json.

    Подбирается по параметрам подобранного двигателя (мощность, ток, напряжение).
    """
    model: str          # Номенклатура (например, "ПЧВ-102-7К5-В")
    p_kw: float         # Номинальная мощность, кВт
    i_nom_a: float      # Номинальный выходной ток, А
    u_in: str = "380/50"  # Входное напряжение
    phase: str = "3ф"     # Число фаз


@dataclass
class CatalogSize:
    """Каталожная карточка типоразмера вентилятора (из catalog.json).

    Описывает типоразмер как комбинацию (series, dn, d_over_dn) с его
    геометрией, массой, шумовым спектром по оборотам и списком допустимых
    двигателей. Аэродинамические кривые Q-P тут не хранятся — они в Impeller.
    """
    series: str                                # Серия ("ВР 86-77" / "ВР 280-46")
    dn: float                                  # Номинальный диаметр DN, ×100 мм
    d_over_dn: float                           # Отношение D/DN
    model: str                                 # Полное имя модели
    max_n: Optional[int] = None                # Макс. частота вращения из моторной гаммы
    min_n_kw: Optional[float] = None           # Мин. мощность двигателя, кВт
    max_n_kw: Optional[float] = None           # Макс. мощность двигателя, кВт
    dims: dict = field(default_factory=dict)   # Габаритные размеры (D,A,B,H,...)
    mass: Optional[float] = None               # Масса, кг
    noise_by_rpm: dict = field(default_factory=dict)  # {rpm: [63..8000, total]} дБ(А)
    motors: List[str] = field(default_factory=list)   # Список марок двигателей
    executions: List[str] = field(default_factory=list)  # Варианты исполнения (О/K/G/...)
    impeller_id: str = ""                      # Ссылка на рабочее колесо (для кривых)

    @property
    def size(self) -> float:
        """Диаметр рабочего колеса — прокси к dn для совместимости фильтров."""
        return self.dn

    def noise_for_rpm(self, rpm: int) -> List[float]:
        """Шумовой спектр для заданных оборотов (или пустой список)."""
        return self.noise_by_rpm.get(str(int(rpm)), [])


@dataclass
class SelectionRequest:
    """Запрос на подбор вентилятора.

    Содержит все входные параметры, которые пользователь задаёт
    для подбора вентилятора: требуемый расход, давление, фильтры
    по серии/размеру/оборотам.
    """
    q_req: float                              # Требуемый расход, м³/ч
    p_req: float                              # Требуемое давление, Па
    pressure_type: PressureType = PressureType.FULL  # Тип давления (полное/статическое)
    d_reg_max: float = 1500.0                 # Макс. дорегулирование, Па
    t_air: float = 20.0                       # Температура воздуха, °C
    series: Tuple[str, ...] = ()              # Фильтр по сериям (пусто = все)
    sizes: Tuple[float, ...] = ()             # Фильтр по размерам (пусто = все)
    rpms: Tuple[int, ...] = ()                # Фильтр по оборотам (пусто = все)
    regulation_mode: RegulationMode = RegulationMode.THROTTLE  # Режим регулирования
    freq_min_hz: float = 20.0                 # Мин. частота ЧРП, Гц (для VFD)
    freq_max_hz: float = 60.0                 # Макс. частота ЧРП, Гц (для VFD)
    q_display: float = 7500.0                 # Расход для отображения графика, м³/ч
    meta: Optional[dict] = None               # Дополнительные метаданные


@dataclass
class FanResult:
    """Результат подбора одного вентилятора.

    Содержит все вычисленные параметры для конкретного вентилятора:
    статус прохождения, давление, КПД, мощность, подобраннный двигатель
    и другие данные для отчёта.
    """
    fan: Fan                                  # Ссылка на вентилятор
    status: ResultStatus = ResultStatus.OK    # Статус подбора
    passed: bool = False                      # Проходит ли условия
    d_reg_pa: float = 0.0                     # Дорегулирование, Па
    eta_req: float = 0.0                      # КПД в рабочей точке (0..1)
    n_shaft_with_margin_w: float = 0.0        # Мощность на валу с запасом, Вт
    motor: Optional[Motor] = None             # Подобранный двигатель
    poly: Optional[np.poly1d] = None          # Полином характеристики (для графика)
    eta_poly: Optional[np.poly1d] = None      # Полином КПД (для графика)
    noise_body_dba: float = 0.0               # Шум корпуса, дБ(А)
    q_work: float = 0.0                       # Расход в рабочей точке, м³/ч
    p_work: float = 0.0                       # Давление в рабочей точке, Па
    # --- VFD (частотное регулирование) ---
    regulation_mode: RegulationMode = RegulationMode.THROTTLE  # Режим регулирования
    f_hz: Optional[float] = None              # Требуемая частота, Гц
    n_rpm: Optional[float] = None             # Обороты при частоте f, об/мин
    q0: Optional[float] = None                # Расход пересечения номинальной кривой и сети, м³/ч
    n_in_w: Optional[float] = None            # Потребляемая мощность, Вт
    vfd: Optional[Vfd] = None                 # Подобранный частотный преобразователь
