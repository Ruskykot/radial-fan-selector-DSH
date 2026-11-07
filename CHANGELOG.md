# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/), версии — SemVer.

## [2.4.0] - 2026-11-07

### Added
- Плагин DSH (`fan-selector-plugin/`, версия пакета `1.0.0`) с REST-маршрутами `/fan-selector/*`,
  инструментом `fan_selector_history` и React-панелью «Подбор вентилятора».
- Режимы: дроссельное (`THROTTLE`), частотное (`VFD`), сравнение (`COMPARE`),
  массовый подбор из CSV.
- Переносимые пути (переменные `FAN_SELECTOR_*`), без hard-code.
- README на русском и английском, демо-GIF, `NOTICE` по данным.

### Changed
- Монорепозиторий: ядро `select-radial-fan` влито в корневой репозиторий.
- Плагин переименован `@local/fan-selector` → `@ruskykot/fan-selector`.
- Ядро `fan_selector` 2.4.0: `Pillow` объявлен явной зависимостью (нужен для PNG-графиков
  и импортируется транзитивно), `requires-python` приведён к `>=3.11`.
- Упаковка: `data/*.json` теперь попадают в wheel (`setup.py` + `MANIFEST.in`),
  поэтому `pip install ./select-radial-fan` даёт рабочий пакет; `DATA_DIR`
  разрешается в `fan_selector/data/` (установка) или `data/` (репозиторий).
- CI: зависимости ставятся из `requirements.txt`, добавлены smoke-тест установленного
  пакета, тесты REST/MCP-логики и сборка `web/`; Dependabot сгруппирован и не
  предлагает мажорные обновления.
- Документация web-виджета приведена в соответствие с кодом (`VITE_MCP_URL`, MCP).

### Removed
- Машинно-специфичные артефакты (`.dsh-acl-recovery`, `output/`) из git.

## [2.3.0] - 2026-10-25

### Added
- Расчётное ядро `fan_selector` (Python, JSON-in/JSON-out).
- MCP-сервер и REST-фолбэк, React-UI `web/`.
- Golden-тесты и исполняемый контракт `data/golden.json`.
