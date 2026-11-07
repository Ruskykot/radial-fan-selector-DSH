# Интеграция с DeepSeek Harness (DSH)

Проект подключается к DSH **как плагин (bundle)**. Плагин сам раздаёт REST-API
`/fan-selector/*`, регистрирует инструмент `fan_selector_history` и вставляет
React-панель «Подбор вентилятора» в интерфейс. Постоянно висящих процессов не
нужно: расчёт запускается одноразово через Python-ядро.

## Структура

- `fan-selector-plugin/` — DSH-бандл (хост `index.js` + клиент `client.js`).
- `select-radial-fan/` — Python-ядро (`fan_selector`) + `data/` + MCP/REST-адаптеры.
- `.dsh/skills/fan-selector/SKILL.md` — навык для агента.

## Требования

- DeepSeek Harness (DSH);
- Node ≥ 20 + pnpm;
- Python ≥ 3.11 с `numpy` и `Pillow` (ядро ставится как пакет: `pip install ./select-radial-fan`).

## Подключение плагина

1. Склонируйте репозиторий.
2. Добавьте бандл в профиль DSH — файл `~/.dsh/profiles/<профиль>/package.json`:

   ```jsonc
   {
     "dependencies": {
       "@ruskykot/fan-selector": "link:<путь_к_репозиторию>/fan-selector-plugin"
     },
     "dsh": {
       "profile": {
         "bundles": ["@ruskykot/fan-selector"]
       }
     }
   }
   ```

   (для npm-публикации вместо `link:` укажите версию, например `"^1.0.0"`).

3. Установите зависимости профиля: `pnpm install` в каталоге профиля (или просто
   перезапустите DSH — он сам установит зависимости).
4. Перезапустите DSH.

Плагин находит ядро автоматически: по расположению плагина или через переменные
окружения `FAN_SELECTOR_RUNNER` / `FAN_SELECTOR_PYTHON` / `FAN_SELECTOR_CORE` /
`FAN_SELECTOR_HISTORY` (см. README).

## Альтернатива: MCP-сервер

Ядро умеет работать как MCP-сервер (stdio / streamable-http), конфиг — `mcp.example.json`:

```bash
cd select-radial-fan
python mcp_stdio.py                # stdio
python mcp_stdio.py streamable-http  # http://127.0.0.1:8000/mcp
```

Для stdio укажите в `mcp.example.json` свой интерпретатор Python (с `mcp`, `numpy` и `Pillow`).

## Проверка

Подбор Q=7500, P=700, «Полное» → ожидается 9 прошедших, лучший
«ВР 280-46-6.3(1DN)-Y-X/750», ΔP=47.56.
