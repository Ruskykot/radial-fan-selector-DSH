# Расчётное ядро fan-selector

Подбор радиальных вентиляторов серий **ВР 86-77** и **ВР 280-46** по рабочей
точке (расход + давление): JSON на входе → JSON на выходе, без I/O-интерфейсов.

> Основной продукт — **плагин DeepSeek Harness**; см. корневой
> [README](../../../README.md) и [`docs/DSH_INTEGRATION.md`](docs/DSH_INTEGRATION.md).

## Установка

```bash
pip install .
```

Зависимости: `numpy` (расчёт) и `Pillow` (PNG-графики) — ставятся автоматически.
Справочники `data/*.json` поставляются вместе с пакетом (в wheel попадают как
`fan_selector/data/`); переменная `FAN_DATA_DIR` позволяет указать свой каталог.

Для разработки удобнее editable-установка: `pip install -e .` (справочники
берутся из каталога `data/` рядом с пакетом).

## Запуск

```bash
python -m fan_selector --json < input.json
```

или из Python:

```python
from fan_selector.select import run_selection
r = run_selection({"q_req": 7500, "p_req": 700, "pressure_type": "FULL"})
```

## Что входит

| Слой | Модули | Назначение |
|---|---|---|
| Ядро | `fan_selector/` | расчёт (дроссельный и ЧРП), JSON-адаптер |
| Данные | `data/` | справочники вентиляторов, колёс, двигателей, ЧРП, каталожные карточки |
| Контракт | `schema/` | JSON Schema входа/выхода |
| API | `mcp_server/`, `mcp_stdio.py` | MCP-сервер и REST-фолбэк |
| UI | `web/` | опциональный самостоятельный React-виджет |

## Тесты

```bash
python tests/test_golden.py
python tests/test_golden_fixture.py
python tests/test_mcp.py
python tests/test_mcp_registration.py
python tests/test_rest.py
```

Только `tests/test_mcp_transport.py` требует MCP SDK
(`pip install -r requirements-mcp.txt`); на Windows для stdio — также `pywin32`.

## Документация

- [docs/CALCULATION.md](docs/CALCULATION.md) — как считается дроссельный расчёт.
- [docs/CALCULATION_VFD.md](docs/CALCULATION_VFD.md) — как считается расчёт в режиме ЧРП.
- [docs/DSH_INTEGRATION.md](docs/DSH_INTEGRATION.md) — интеграция с DSH.
- `docs/archive/` — исторические дизайн-заметки (MCP.md, ARTIFACT_REACT.md,
  SYNTHESIS.md, VFD_TZ.md, ARTIFACT_WASM.md, REDESIGN.md).

## Данные и лицензия

Справочники `data/*.json` описаны в [`NOTICE`](../../../NOTICE);
код — Apache-2.0 (см. [`LICENSE`](../../../LICENSE)).

`start.ps1` — удобный запуск (MCP + UI + REST) только для Windows; на
Linux/macOS используйте команды выше.
