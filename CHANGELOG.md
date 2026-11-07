# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/), версии — SemVer.

## [Unreleased]

### Added
- Плагин DSH (`fan-selector-plugin/`) с REST-маршрутами `/fan-selector/*`,
  инструментом `fan_selector_history` и React-панелью «Подбор вентилятора».
- Режимы: дроссельное (`THROTTLE`), частотное (`VFD`), сравнение (`COMPARE`),
  массовый подбор из CSV.
- Переносимые пути (переменные `FAN_SELECTOR_*`), без hard-code.
- README на русском и английском, демо-GIF, `NOTICE` по данным.

### Changed
- Монорепозиторий: ядро `select-radial-fan` влито в корневой репозиторий.
- Плагин переименован `@local/fan-selector` → `@ruskykot/fan-selector`.

### Removed
- Машинно-специфичные артефакты (`.dsh-acl-recovery`, `output/`) из git.

## [2.3.0] - 2026-10-25

### Added
- Расчётное ядро `fan_selector` (Python, JSON-in/JSON-out).
- MCP-сервер и REST-фолбэк, React-UI `web/`.
- Golden-тесты и исполняемый контракт `data/golden.json`.
