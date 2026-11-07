---
name: fan-selector
description: Подбор радиальных вентиляторов ВР 86-77 и ВР 280-46 по расходу и давлению. Использовать, когда пользователь просит подобрать вентилятор, узнать двигатель, мощность, габариты или массу.
---

# Подбор радиальных вентиляторов

Расчётное ядро `fan_selector` живёт в каталоге
`fan-selector-plugin/core/select-radial-fan/` (Python, JSON-in/JSON-out). Навык —
тонкий указатель: расчёт выполняет ядро, а не пересказ формул в чате.

## Приоритетный путь

1. Если доступен интерактивный виджет «Подбор вентилятора» (панель DSH-плагина) —
   предложи пользователю открыть его: ввод Q/P и результат происходят в виджете.
2. Если доступны MCP-инструменты `fan-selector` — вызови их:
   - `select_fan(q_req, p_req, pressure_type, d_reg_max, series, sizes, rpms, regulation_mode, freq_min_hz, freq_max_hz)` — подбор;
   - `lookup_catalog(series, dn, d_over_dn)` — каталожные карточки;
   - `fan_chart(q_req, p_req, pressure_type)` — PNG-график.
   Ресурсы `fan://data/*` — справочники.
   `regulation_mode`: `THROTTLE` (дроссельный, по умолчанию) или `VFD`
   (частотное регулирование с подбором частотного преобразователя; задаётся
   диапазон `freq_min_hz`/`freq_max_hz`).
3. Историю подборов читай инструментом `fan_selector_history`
   (`action`: `list` — вернуть записи, `clear` — очистить).
4. Уточни у пользователя только недостающее (расход Q, м³/ч, и давление P, Па;
   тип давления FULL/STATIC; при необходимости режим регулирования и фильтры),
   не подставляя свои числа.

## Фолбэк (когда MCP/виджет недоступны)

Запусти ядро одним процессом из каталога `fan-selector-plugin/core/select-radial-fan/`:

```text
cd fan-selector-plugin/core/select-radial-fan
echo {"q_req":7500,"p_req":700,"pressure_type":"FULL"} | python -m fan_selector --json
```

или прямым вызовом (путь к ядру вычисляется, а не зашит):

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path("fan-selector-plugin/core/select-radial-fan").resolve()))
from fan_selector.select import run_selection, chart_selection
r = run_selection({"q_req": 7500, "p_req": 700, "pressure_type": "FULL"})
```

`pressure_type`: `FULL` (полное) или `STATIC` (статическое).
График: `chart_selection(...)["chart_png_base64"]` → base64 → PNG.

## Ключи результата

- `summary`: `total`, `passed`, `best_model`, `best_d_reg_pa`.
- `results[]`: `model`, `dn`, `d_over_dn`, `max_n`, `d_reg_pa`, `eta_req`,
  `n_shaft_with_margin_w`, `motor`, `dims`, `mass`, `executions`, `noise_by_rpm`.
- В режиме `VFD` дополнительно: `regulation_mode`, `f_hz`, `n_rpm`, `q0`,
  `n_in_w`, `vfd` (`model`, `p_kw`, `i_nom_a`).
- `status`: `OK` — подходит; иначе — причина отказа (русский текст; для VFD —
  `FREQ_BELOW_MIN`/`FREQ_ABOVE_MAX`/`VFD_NOT_FOUND` и др.).

## Данные (не менять)

- `data/fans.json` + `data/impellers.json` — 66 вентиляторов и кривых.
- `data/motors.json` — 55 двигателей; `data/vfd.json` — частотные преобразователи.
- `data/catalog.json` — массо-габариты.
- `data/golden.json` — исполняемый контракт (эталонные ответы).
