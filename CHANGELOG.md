# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/), версии — SemVer.

## [1.0.0] - 2026-11-07

Первая публикация плагина в npm:
[@rusky_kot/fan-selector](https://www.npmjs.com/package/@rusky_kot/fan-selector)
(внутри — расчётное ядро `fan_selector` 2.4.0).

### Added
- npm-канал распространения: Python-ядро и справочники поставляются **внутри**
  пакета `@rusky_kot/fan-selector` (`fan-selector-plugin/core/`), поэтому после
  установки плагина в профиль DSH `pip install` ядра не требуется.
- `engines.dsh` (`>=0.2.0-0`) в пакете плагина — DSH проверяет совместимость при
  установке; в пакет добавлены `LICENSE` и `README.md` для страницы npm.
- Проверка Python-окружения в плагине: при отсутствии Python 3.11+ / `numpy` /
  `Pillow` маршруты `/fan-selector/*` отвечают HTTP 500 с кодом `ENV` и понятным
  текстом с командой установки.
- Дефолтная конфигурация в `fan_selector/config.py`: при отсутствии
  `data/config.json` расчёт работает на значениях по умолчанию (с предупреждением).

### Changed
- Раскладка: ядро перенесено в `fan-selector-plugin/core/select-radial-fan/`,
  раннер — в `fan-selector-plugin/core/run_once.py` (сознательно рядом с ядром,
  чтобы работал штатный фолбэк раннера).
- Пакет плагина переименован `@ruskykot/fan-selector` → `@rusky_kot/fan-selector`
  (личный scope npm-аккаунта `rusky_kot`; org `ruskykot` в npm не создавался).
  Обновлены `package.json`, `cordis.patch.yml`, `client.js` и все команды установки.
- `index.js`: пути вычисляются от каталога плагина (`CORE_DIR`), `cwd` спавна —
  каталог плагина; старый `PROJECT_ROOT` удалён.
- `config.py`: путь к `config.json` строится относительно пакета
  (`FAN_CONFIG_PATH` → `_MEIPASS` при наличии файла → `data/config.json` рядом с пакетом).
- README переписан под npm-канал: «Установка (пользователям)» начинается с
  установки плагина, клонирование и `pip install` ядра — раздел «Разработка».
- MCP-слой помечен экспериментальным; extra требует `mcp[cli]>=2.0`.
- Демо-GIF оптимизированы: 20,59 МБ → 2,83 МБ (схлопнуты статичные кадры
  скринкастов, палитра 32–128 цветов, разрешение и длительность сохранены).
- CI: `pnpm install --frozen-lockfile`; тест регистрации MCP больше не подменяет
  SDK заглушкой — без SDK он даёт SKIP, с SDK проверяет реальный сервер.
- Web-виджет: при ошибке подключения кэш MCP-клиента сбрасывается (переподключение).
- Web-виджет: `vite` 5.4 → 8.3, `@vitejs/plugin-react` 4.7 → 6.2 — закрыты
  17 алертов Dependabot по dev-зависимостям сборки (в npm-пакет не попадают);
  требования к сборке подняты: Node ≥ 20.19, pnpm ≥ 10.
- HTTP-гигиена: убран `Access-Control-Allow-Origin: *` у плагина и фолбэков,
  добавлен лимит тела запроса 5 МБ.

### Removed
- Легаси-поля конфигурации `pdf_output_dir`, `db_path`, `t_air_min`/`t_air_max`
  (никем не читались). Старые `config.json` с этими полями продолжают загружаться —
  неизвестные ключи игнорируются.
- Машинно-специфичные артефакты (`.dsh-acl-recovery`, `output/`) из git.

### Fixed
- Единая лицензия Apache-2.0: в `docs/CALCULATION.md` ошибочно указывалась MIT.
- `start.ps1`: добавлен UTF-8 BOM (корректная кириллица в Windows PowerShell 5.1).
- Архив устаревших design-документов (`docs/archive/`), битые относительные ссылки.

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
  поэтому `pip install` ядра даёт рабочий пакет; `DATA_DIR`
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
