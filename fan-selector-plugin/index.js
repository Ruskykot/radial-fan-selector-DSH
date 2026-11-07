/** Host half of the fan-selector bundle.

 * Serves the fan selection backend directly from the DSH web server, so it
 * survives every restart without any separate process:
 *   - POST /fan-selector/{select,chart,compare,catalog} -> one-shot Python core
 *     (spawned through the DSH `subprocess` service);
 *   - GET/POST/DELETE /fan-selector/history -> durable history (Node fs);
 * and registers the agent tool `fan_selector_history`.
 */
import { existsSync } from 'node:fs';
import { readFile, writeFile } from 'node:fs/promises';
import { homedir } from 'node:os';
import { parse as parseQuery } from 'node:querystring';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Пути вычисляются от фактического расположения плагина (не зашиты в код),
// поэтому пакет можно ставить в любой профиль DSH и на любую ОС.
// Расчётное ядро (Python) поставляется внутри пакета в каталоге core/.
// Переопределение через переменные окружения:
//   FAN_SELECTOR_RUNNER  — путь к run_once.py (JSON-in/JSON-out раннер);
//   FAN_SELECTOR_PYTHON  — интерпретатор Python (нужен numpy и Pillow);
//   FAN_SELECTOR_HISTORY — файл истории (по умолчанию ~/.fan-selector-history.json);
//   FAN_SELECTOR_CORE    — путь к пакету fan_selector (читается в run_once.py).
const PLUGIN_DIR = path.dirname(fileURLToPath(import.meta.url));
const CORE_DIR = path.join(PLUGIN_DIR, 'core');
const RUN_ONCE = process.env.FAN_SELECTOR_RUNNER || path.join(CORE_DIR, 'run_once.py');
const HISTORY_PATH = process.env.FAN_SELECTOR_HISTORY || path.join(homedir(), '.fan-selector-history.json');
const PYTHON = process.env.FAN_SELECTOR_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const HISTORY_CAP = 5000;

// Тексты ошибок окружения (показываются в панели и в ответе API).
const CORE_MISSING_MESSAGE =
  'Расчётное ядро не найдено в каталоге плагина (ожидался core/run_once.py). ' +
  'Переустановите плагин или задайте FAN_SELECTOR_RUNNER.';
const PYTHON_MISSING_MESSAGE =
  'Python не найден. Установите Python 3.11+ (python.org) и выполните: pip install numpy pillow. ' +
  'Либо задайте FAN_SELECTOR_PYTHON.';
const PYTHON_LIBS_MESSAGE =
  'Python 3.11+ с библиотеками numpy и Pillow не найден. ' +
  'Установите Python 3.11+ (python.org) и выполните: pip install numpy pillow. ' +
  'Либо задайте FAN_SELECTOR_PYTHON.';

export const inject = ['tools', 'webServer', 'subprocess'];

// ---------------------------------------------------------------------------
// Проверка окружения Python (один раз на старте плагина; перезапуск DSH
// проверяет заново — так пользователь может доустановить Python/библиотеки)
// ---------------------------------------------------------------------------
const PYTHON_CHECK_SCRIPT =
  'import sys; print(sys.version_info[0], sys.version_info[1]); import numpy, PIL';

let pythonEnvPromise = null;

function checkPythonEnv(subprocess) {
  if (pythonEnvPromise) return pythonEnvPromise;
  pythonEnvPromise = (async () => {
    if (!existsSync(RUN_ONCE)) {
      return CORE_MISSING_MESSAGE;
    }
    let handle;
    try {
      handle = subprocess.spawn({
        argv: [PYTHON, '-c', PYTHON_CHECK_SCRIPT],
        cwd: PLUGIN_DIR,
        stdio: {
          stdin: { data: '' },
          stdout: { maxBytes: 64 * 1024 },
          stderr: { maxBytes: 64 * 1024 },
        },
        graceMs: 8000,
      });
    } catch (e) {
      // Спавн не удался: интерпретатор не найден (в Windows это также ловит
      // заглушку Microsoft Store, которая завершается с ошибкой запуска).
      return PYTHON_MISSING_MESSAGE;
    }
    let outcome;
    try {
      outcome = await handle.done;
    } catch (e) {
      return PYTHON_MISSING_MESSAGE;
    }
    if (outcome.exitCode !== 0) {
      return PYTHON_LIBS_MESSAGE;
    }
    return null;
  })();
  return pythonEnvPromise;
}


// ---------------------------------------------------------------------------
// История (файл в корне рабочей области; переживает перезапуск DSH)
// ---------------------------------------------------------------------------
async function readHistory() {
  try {
    const raw = await readFile(HISTORY_PATH, 'utf8');
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  } catch (e) {
    return [];
  }
}

async function writeHistory(entries) {
  await writeFile(HISTORY_PATH, JSON.stringify(entries, null, 2), 'utf8');
}

// ---------------------------------------------------------------------------
// Одноразовый расчёт через штатный subprocess (JSON на stdin -> JSON на stdout)
// ---------------------------------------------------------------------------
function runPython(subprocess, op, payload, graceMs = 120000) {
  const input = JSON.stringify({ op, payload });
  if (!existsSync(RUN_ONCE)) {
    throw new Error(CORE_MISSING_MESSAGE);
  }
  const argv = [PYTHON, RUN_ONCE];
  const handle = subprocess.spawn({
    argv,
    cwd: PLUGIN_DIR,
    stdio: {
      stdin: { data: input },
      stdout: { maxBytes: 80 * 1024 * 1024 },
      stderr: { maxBytes: 2 * 1024 * 1024 },
    },
    graceMs,
  });
  return handle.done.then((outcome) => {
    const stdout = handle.collected.stdout ? handle.collected.stdout.readFrom(0).text : '';
    const stderr = handle.collected.stderr ? handle.collected.stderr.readFrom(0).text : '';
    if (outcome.exitCode !== 0) {
      throw new Error((stderr || '').trim() || ('exit code ' + outcome.exitCode));
    }
    try {
      return JSON.parse(stdout);
    } catch (e) {
      throw new Error('Некорректный ответ расчёта: ' + String(stdout).slice(0, 200));
    }
  });
}

// ---------------------------------------------------------------------------
// HTTP-утилиты
// ---------------------------------------------------------------------------
function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

function sendJson(res, obj, status = 200) {
  const body = JSON.stringify(obj);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Content-Length': Buffer.byteLength(body),
  });
  res.end(body);
}

// ---------------------------------------------------------------------------
// Маршруты (пересоздаются при каждой активации плагина, т.е. при каждом старте)
// ---------------------------------------------------------------------------
function registerRoutes(webServer, subprocess) {
  const disposers = [];
  const reg = (route) => disposers.push(webServer.register(route));
  for (const op of ['select', 'chart', 'compare', 'catalog']) {
    reg({
      kind: 'exact',
      path: '/fan-selector/' + op,
      handler: async (req, res) => {
        if (req.method !== 'POST') {
          return sendJson(res, { error: { code: 'METHOD', message: 'method not allowed' } }, 405);
        }
        const envProblem = await checkPythonEnv(subprocess);
        if (envProblem) {
          return sendJson(res, {
            schema: 'fan-result/v1',
            error: { code: 'ENV', message: envProblem },
          }, 500);
        }
        try {
          const payload = JSON.parse((await readBody(req)) || '{}');
          const result = await runPython(subprocess, op, payload);
          sendJson(res, result);
        } catch (e) {
          sendJson(res, {
            schema: 'fan-result/v1',
            error: { code: 'CALC_ERROR', message: String((e && e.message) || e) },
          }, 500);
        }
      },
    });
  }

  // Эталонный CSV-шаблон для массового подбора (скачивание).
  const CSV_TEMPLATE = '\uFEFF' + [
    'Система;Комментарий;Расход Q, м³/ч;Давление P, Па;Тип давления;Режим;Дорегулирование ΔP, Па;Температура, °C;f мин, Гц;f макс, Гц',
    'П1;приток;7500;700;Полное;Дроссельное;1500;20;20;60',
    'П2;вытяжка;12000;850;Полное;ЧРП;1500;20;30;50',
  ].join('\r\n') + '\r\n';

  reg({
    kind: 'exact',
    path: '/fan-selector/template.csv',
    handler: (req, res) => {
      if (req.method !== 'GET') {
        res.writeHead(405, { 'Content-Type': 'application/json; charset=utf-8' });
        return res.end(JSON.stringify({ error: { code: 'METHOD', message: 'method not allowed' } }));
      }
      const body = Buffer.from(CSV_TEMPLATE, 'utf8');
      const filename = 'шаблон_подбора.csv';
      res.writeHead(200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Length': body.length,
        'Content-Disposition': `attachment; filename="template.csv"; filename*=UTF-8''${encodeURIComponent(filename)}`,
        'Access-Control-Allow-Origin': '*',
      });
      res.end(body);
    },
  });

  // Массовый подбор: превью (парсинг) и расчёт.
  for (const [op, path] of [['parse_csv', '/fan-selector/batch/parse'], ['batch', '/fan-selector/batch']]) {
    reg({
      kind: 'exact',
      path,
      handler: async (req, res) => {
        if (req.method !== 'POST') {
          return sendJson(res, { error: { code: 'METHOD', message: 'method not allowed' } }, 405);
        }
        try {
          const payload = JSON.parse((await readBody(req)) || '{}');
          const result = await runPython(subprocess, op, payload, 600000);
          sendJson(res, result);
        } catch (e) {
          sendJson(res, {
            schema: 'fan-result/v1',
            error: { code: 'CALC_ERROR', message: String((e && e.message) || e) },
          }, 500);
        }
      },
    });
  }

  reg({
    kind: 'exact',
    path: '/fan-selector/history/batch',
    handler: async (req, res) => {
      if (req.method !== 'POST') {
        return sendJson(res, { error: { code: 'METHOD', message: 'method not allowed' } }, 405);
      }
      try {
        const body = JSON.parse((await readBody(req)) || '{}');
        const incoming = Array.isArray(body.entries) ? body.entries : [];
        let entries = await readHistory();
        if (body.replaceByFileName && body.fileName) {
          entries = entries.filter((e) => e.fileName !== body.fileName);
        }
        const ids = new Set(incoming.map((e) => e.id).filter(Boolean));
        entries = entries.filter((e) => !ids.has(e.id));
        entries = incoming.concat(entries).slice(0, HISTORY_CAP);
        await writeHistory(entries);
        sendJson(res, { items: entries });
      } catch (e) {
        sendJson(res, { error: { code: 'HISTORY_ERROR', message: String((e && e.message) || e) } }, 500);
      }
    },
  });

  reg({
    kind: 'exact',
    path: '/fan-selector/history',
    handler: async (req, res) => {
      try {
        if (req.method === 'GET') {
          sendJson(res, { items: await readHistory() });
        } else if (req.method === 'POST') {
          const entry = JSON.parse((await readBody(req)) || '{}');
          let entries = await readHistory();
          entries = entries.filter((e) => e.id !== entry.id);
          entries.unshift(entry);
          entries = entries.slice(0, HISTORY_CAP);
          await writeHistory(entries);
          sendJson(res, { items: entries });
        } else if (req.method === 'DELETE') {
          const query = parseQuery((req.url || '').split('?')[1] || '');
          let entries = await readHistory();
          if (query.id) entries = entries.filter((e) => e.id !== query.id);
          else entries = [];
          await writeHistory(entries);
          sendJson(res, { items: entries });
        } else {
          sendJson(res, { error: { code: 'METHOD', message: 'method not allowed' } }, 405);
        }
      } catch (e) {
        sendJson(res, { error: { code: 'HISTORY_ERROR', message: String((e && e.message) || e) } }, 500);
      }
    },
  });

  return disposers;
}

export function apply(ctx) {
  const disposers = registerRoutes(ctx.webServer, ctx.subprocess);

  ctx.tools.register({
    name: 'fan_selector_history',
    description:
      'История подборов радиальных вентиляторов (ВР 86-77 / ВР 280-46). ' +
      'Возвращает сохранённые подборы: систему и комментарий, расход/давление, ' +
      'режим (дроссельное / ЧРП / сравнение), диапазон частоты и выбранный ' +
      'вентилятор. Действие clear очищает историю.',
    parameters: {
      type: 'object',
      properties: {
        action: {
          type: 'string',
          enum: ['list', 'clear'],
          description: 'list — вернуть историю подборов; clear — очистить историю.',
        },
        limit: {
          type: 'integer',
          description: 'Максимум возвращаемых записей (по умолчанию 100, максимум 500).',
        },
      },
      required: ['action'],
    },
    output: {
      schema: {
        type: 'object',
        properties: {
          count: { type: 'integer' },
          items: { type: 'array' },
        },
        required: ['count', 'items'],
      },
      render(args, value) {
        const items = (value && value.items) || [];
        const count = (value && value.count) != null ? value.count : items.length;
        if (!items.length) {
          return [{ type: 'text', text: 'История подборов пуста.' }];
        }
        const lines = items.map((e, i) => {
          const mode = e.mode === 'THROTTLE' ? 'дроссельное' : e.mode === 'VFD' ? 'ЧРП' : 'сравнение';
          const when = e.ts ? new Date(e.ts).toLocaleString('ru-RU') : '?';
          const meta = [];
          if (e.system) meta.push(`система: ${e.system}`);
          if (e.comment) meta.push(`комментарий: ${e.comment}`);
          const metaStr = meta.length ? ` ${meta.join(', ')} |` : '';
          let line = `${i + 1}. [${when}]${metaStr} Q=${e.q} м³/ч, P=${e.p} Па, ${mode}`;
          if (e.mode !== 'THROTTLE' && e.freq_min_hz != null && e.freq_max_hz != null) {
            line += `, f=${e.freq_min_hz}–${e.freq_max_hz} Гц`;
          }
          if (e.pinnedModel) line += ` | выбран: ${e.pinnedModel}`;
          else line += ' | нет подходящих';
          return line;
        });
        const extra = count > items.length ? `\n(показаны первые ${items.length} из ${count})` : '';
        return [{ type: 'text', text: `История подборов (${count}):\n${lines.join('\n')}${extra}` }];
      },
    },
    async execute(args) {
      if (args && args.action === 'clear') {
        await writeHistory([]);
        return { count: 0, items: [] };
      }
      const all = await readHistory();
      const limit = Math.max(1, Math.min(500, Number(args && args.limit) || 100));
      return { count: all.length, items: all.slice(0, limit) };
    },
  });
  ctx.effect(() => () => {
    for (const d of disposers) {
      if (typeof d === 'function') d();
    }
  });
}
