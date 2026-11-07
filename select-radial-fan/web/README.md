# React-артефакт подбора вентиляторов

Интерактивный ввод/вывод вместо чат-диалога: форма (Q/P/тип/фильтры) → таблица +
SVG-график. Расчёт выполняет Python-ядро `fan_selector` через API; виджет —
тонкий клиент.

## Стек

Vite + React + TypeScript. График — ручной SVG (без внешних библиотек).

## Запуск

```bash
cd web
pnpm install
pnpm dev        # http://localhost:5173
pnpm build      # статический билд в dist/
```

## API

Виджет делает `POST {VITE_API_BASE}/select` (по умолчанию `http://localhost:8000`)
и ожидает `fan-result/v1` (см. `schema/result.schema.json`).

Два способа поднять API-сервер:

1. **REST-фолбэк** (stdlib, без зависимостей):
   ```bash
   python -m mcp_server.rest        # 127.0.0.1:8000
   ```
2. **MCP-сервер** (основной транспорт):
   ```bash
   pip install "mcp[cli]"
   python -m mcp run mcp_server/server.py --transport streamable-http
   ```
   В этом случае виджет следует переключить с REST на MCP-клиент
   (`@modelcontextprotocol/sdk`) — см. `src/api.ts`.

Переменная `VITE_API_BASE` задаёт адрес API (`.env`: `VITE_API_BASE=http://host:port`).

## Структура

```
web/
├── index.html
├── vite.config.ts / tsconfig*.json / package.json
└── src/
    ├── main.tsx, App.tsx
    ├── types.ts      # типы из schema/result.schema.json
    ├── config.ts     # границы валидации + списки фильтров
    ├── api.ts        # транспорт (REST / MCP)
    └── components/
        ├── FanForm.tsx       # ввод
        ├── ResultTable.tsx   # таблица прошедших
        └── FanChart.tsx      # SVG-график P(Q)
```
