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

Виджет — **MCP-клиент**: он подключается к MCP-серверу `fan-selector` по
streamable-http и вызывает инструмент `select_fan` (см. `src/api.ts`,
`@modelcontextprotocol/sdk`). Результат — контракт `fan-result/v1`
(см. `schema/result.schema.json`).

Перед запуском виджета поднимите MCP-сервер из корня `select-radial-fan`:

```bash
pip install -r requirements.txt -r requirements-mcp.txt
python mcp_stdio.py streamable-http      # 127.0.0.1:8000/mcp
```

Адрес сервера задаётся переменной `VITE_MCP_URL` (по умолчанию
`http://127.0.0.1:8000/mcp`):

```bash
# .env
VITE_MCP_URL=http://127.0.0.1:8000/mcp
```

REST-фолбэк (`python run-rest.py 8100`, `mcp_server/rest.py`) виджет **не**
использует — он нужен сторонним HTTP-клиентам.

## Структура

```
web/
├── index.html
├── vite.config.ts / tsconfig*.json / package.json
└── src/
    ├── main.tsx, App.tsx
    ├── types.ts      # типы из schema/result.schema.json
    ├── config.ts     # границы валидации + списки фильтров
    ├── api.ts        # MCP-транспорт (streamable-http)
    └── components/
        ├── FanForm.tsx       # ввод
        ├── ResultTable.tsx   # таблица прошедших
        └── FanChart.tsx      # SVG-график P(Q)
```
