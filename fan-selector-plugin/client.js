window.__ModuleLoader__.load({
  id: '@ruskykot/fan-selector',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const useState = React.useState;
    const useEffect = React.useEffect;
    const useRef = React.useRef;

    const PANEL_ID = 'fan-selector';
    // Бэкенд раздаёт Host-половина плагина через маршруты DSH (тот же origin).
    const API_BASE = '/fan-selector';
    const HISTORY_CAP = 5000;

    // ------------------------------------------------------------------
    // Иконка левой панели (sidebar.panellist).
    // ------------------------------------------------------------------
    function FanIcon(props) {
      const size = props.size || 20;
      const color = props.active
        ? 'var(--dsw-alias-brand-primary)'
        : 'var(--dsw-alias-label-secondary)';
      const blade = h('path', {
        d: 'M12 9.2 C 10.3 8.2, 10.3 3.6, 12 2.7',
        strokeLinecap: 'round',
      });
      return h(
        'svg',
        {
          viewBox: '0 0 24 24', width: size, height: size,
          fill: 'none', stroke: color, strokeWidth: 1.7, strokeLinecap: 'round',
          'aria-hidden': true, style: { display: 'block' },
        },
        h('circle', { cx: 12, cy: 12, r: 9.2 }),
        blade,
        h('g', { transform: 'rotate(90 12 12)' }, blade),
        h('g', { transform: 'rotate(180 12 12)' }, blade),
        h('g', { transform: 'rotate(270 12 12)' }, blade),
        h('circle', { cx: 12, cy: 12, r: 2.5, fill: color, stroke: 'none' }),
      );
    }

    function fmt(v, digits) {
      if (v === null || v === undefined || !Number.isFinite(v)) return '—';
      return Number(v).toFixed(digits);
    }

    // Фактическая рабочая точка вентилятора: «Q / P» в одну колонку через слеш.
    function workPointText(src) {
      const q = src && src.q_work;
      const p = src && src.p_work;
      const qs = (q === null || q === undefined || !Number.isFinite(q)) ? '—' : String(Math.round(q));
      let ps = '—';
      if (p !== null && p !== undefined && Number.isFinite(p)) {
        ps = Number(p).toFixed(1);
        if (ps.endsWith('.0')) ps = ps.slice(0, -2);
      }
      return qs + ' / ' + ps;
    }

    // ---- история: durable-хранилище через REST-сервер (файл в корне проекта) ----
    function fetchHistoryList() {
      return fetch(API_BASE + '/history')
        .then((r) => r.json())
        .then((d) => (d && Array.isArray(d.items)) ? d.items : [])
        .catch(() => []);
    }
    function postHistory(entry) {
      return fetch(API_BASE + '/history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(entry),
      }).then((r) => r.json())
        .then((d) => (d && Array.isArray(d.items)) ? d.items : null)
        .catch(() => null);
    }
    function postHistoryBatch(entries, fileName) {
      return fetch(API_BASE + '/history/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fileName, replaceByFileName: true, entries }),
      }).then((r) => r.json())
        .then((d) => (d && Array.isArray(d.items)) ? d.items : null)
        .catch(() => null);
    }
    function deleteHistory(id) {
      const url = id ? (API_BASE + '/history?id=' + encodeURIComponent(id)) : (API_BASE + '/history');
      return fetch(url, { method: 'DELETE' })
        .then((r) => r.json())
        .then((d) => (d && Array.isArray(d.items)) ? d.items : null)
        .catch(() => null);
    }
    function tsLabel(ts) {
      const d = new Date(ts);
      const p = (n) => String(n).padStart(2, '0');
      return p(d.getDate()) + '.' + p(d.getMonth() + 1) + '.' + d.getFullYear() +
        ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
    }
    function fmtDims(dims) {
      if (!dims || typeof dims !== 'object') return '—';
      const parts = Object.entries(dims).map(([k, v]) => k + '=' + (v == null ? '—' : v));
      return parts.length ? parts.join(', ') : '—';
    }
    function fmtList(list) {
      if (!Array.isArray(list) || !list.length) return '—';
      return list.join(', ');
    }

    function modeLabelText(mode) {
      return mode === 'THROTTLE' ? 'Дроссельное' : mode === 'VFD' ? 'ЧРП' : 'Сравнение';
    }

    function readFileAsBase64(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const s = String(reader.result || '');
          const i = s.indexOf(',');
          resolve(i >= 0 ? s.slice(i + 1) : s);
        };
        reader.onerror = () => reject(reader.error || new Error('ошибка чтения файла'));
        reader.readAsDataURL(file);
      });
    }

    // ---- значения/текст для одиночных режимов ----
    function cellText(r, key) {
      const motor = r.motor || {};
      const vfd = r.vfd || {};
      switch (key) {
        case 'model': return r.model;
        case 'work_point': return workPointText(r);
        case 'max_n': return fmt(r.max_n, 0);
        case 'd_reg_pa': return fmt(r.d_reg_pa, 1);
        case 'eta_req': return r.eta_req != null ? fmt(r.eta_req * 100, 1) : '—';
        case 'motor': return motor.name || '—';
        case 'n_kw': return motor.n_kw != null ? fmt(motor.n_kw, 1) : '—';
        case 'noise_body_dba': return r.noise_body_dba != null ? fmt(r.noise_body_dba, 0) : '—';
        case 'f_hz': return fmt(r.f_hz, 2);
        case 'n_rpm': return fmt(r.n_rpm, 0);
        case 'vfd': return vfd.model || '—';
        case 'n_in_w': return r.n_in_w != null ? fmt(r.n_in_w / 1000, 2) : '—';
        default: return '';
      }
    }

    function sortValue(r, key) {
      const motor = r.motor || {};
      const vfd = r.vfd || {};
      switch (key) {
        case 'model': return r.model || '';
        case 'work_point': return r.p_work;
        case 'max_n': return r.max_n;
        case 'd_reg_pa': return r.d_reg_pa;
        case 'eta_req': return r.eta_req;
        case 'motor': return motor.name || '';
        case 'n_kw': return motor.n_kw;
        case 'noise_body_dba': return r.noise_body_dba;
        case 'f_hz': return r.f_hz;
        case 'n_rpm': return r.n_rpm;
        case 'vfd': return vfd.model || '';
        case 'n_in_w': return r.n_in_w;
        default: return null;
      }
    }

    // ---- значения/текст для режима сравнения (одна строка = одна позиция) ----
    function compareMotorName(r) {
      const src = r.t || r.v;
      const motor = (src && src.motor) || {};
      return motor.name || '';
    }

    function compareCellText(r, key) {
      const t = r.t;
      const v = r.v;
      switch (key) {
        case 'model': return r.model;
        case 'work_point': return workPointText(r.t || r.v);
        case 'mode': return r.mode === 'THROTTLE' ? 'Дроссель' : 'ЧРП';
        case 'd_reg_pa': return t ? fmt(t.d_reg_pa, 1) : '—';
        case 'f_hz': return v ? fmt(v.f_hz, 2) : '—';
        case 'motor': {
          const src = t || v;
          const motor = (src && src.motor) || {};
          if (!motor.name) return '—';
          return motor.n_kw != null
            ? motor.name + ' · ' + fmt(motor.n_kw, 1) + ' кВт'
            : motor.name;
        }
        case 'vfd': return v ? ((v.vfd || {}).model || '—') : '—';
        default: return '';
      }
    }

    function compareSortValue(r, key) {
      const t = r.t;
      const v = r.v;
      switch (key) {
        case 'model': return r.model || '';
        case 'work_point': {
          const src = r.t || r.v;
          return src ? src.p_work : null;
        }
        case 'mode': return r.mode === 'THROTTLE' ? 0 : 1;
        case 'd_reg_pa': return t ? t.d_reg_pa : null;
        case 'f_hz': return v ? v.f_hz : null;
        case 'motor': return compareMotorName(r);
        case 'vfd': return v ? ((v.vfd || {}).model || '') : '';
        default: return null;
      }
    }

    function compareGeneric(a, b, key, dir, getter) {
      const va = getter(a, key);
      const vb = getter(b, key);
      const na = va === null || va === undefined || va === '';
      const nb = vb === null || vb === undefined || vb === '';
      if (na && nb) return 0;
      if (na) return 1;
      if (nb) return -1;
      const cmp = (typeof va === 'number' && typeof vb === 'number')
        ? va - vb
        : String(va).localeCompare(String(vb), 'ru');
      return dir === 'asc' ? cmp : -cmp;
    }

    const CSS = `
      .fs-panel { height: 100%; overflow: auto; box-sizing: border-box; padding: 24px 28px 48px; color: var(--dsw-alias-label-primary); }
      .fs-inner { max-width: 1040px; margin: 0 auto; }
      .fs-title { margin: 0 0 4px; font-size: 20px; font-weight: 600; }
      .fs-subtitle { margin: 0 0 18px; font-size: 13px; color: var(--dsw-alias-label-secondary); }
      .fs-form { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; padding: 16px; border: 1px solid var(--dsw-alias-border-l1); border-radius: 10px; background: var(--dsw-alias-bg-layer-1); }
      .fs-field { display: flex; flex-direction: column; gap: 6px; }
      .fs-label { font-size: 12px; color: var(--dsw-alias-label-secondary); }
      .fs-input, .fs-select { height: 32px; padding: 0 10px; box-sizing: border-box; border: 1px solid var(--dsw-alias-border-l2); border-radius: 6px; background: var(--dsw-alias-bg-base); color: var(--dsw-alias-label-primary); font-size: 14px; font-family: inherit; }
      .fs-input { width: 120px; }
      .fs-input-wide { width: 320px; }
      .fs-select { min-width: 190px; }
      .fs-row { display: flex; gap: 12px; flex-wrap: wrap; }
      .fs-btn { height: 32px; padding: 0 18px; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit; border: 1px solid var(--dsw-alias-brand-primary); color: var(--dsw-alias-brand-primary); background: transparent; }
      .fs-btn:disabled { opacity: .55; cursor: default; }
      .fs-btn-next { color: var(--dsw-alias-label-secondary); border: 1px dashed var(--dsw-alias-border-l2); }
      .fs-btn-next:hover { color: var(--dsw-alias-brand-primary); border-color: var(--dsw-alias-brand-primary); }
      .fs-next { margin-top: 22px; }
      .fs-btn-ghost { height: 28px; padding: 0 12px; border-radius: 6px; font-size: 12px; cursor: pointer; font-family: inherit; border: 1px solid var(--dsw-alias-border-l2); color: var(--dsw-alias-label-secondary); background: transparent; }
      .fs-btn-ghost:hover { color: var(--dsw-alias-label-primary); }
      .fs-error { margin-top: 16px; padding: 10px 12px; font-size: 13px; border: 1px solid var(--dsw-alias-state-error-primary); border-radius: 8px; color: var(--dsw-alias-state-error-primary); }
      .fs-block { margin-top: 22px; }
      .fs-block-title { margin: 0 0 6px; padding-bottom: 6px; font-size: 15px; font-weight: 600; border-bottom: 1px solid var(--dsw-alias-border-l1); }
      .fs-summary { margin: 6px 0 6px; font-size: 14px; }
      .fs-summary b { color: var(--dsw-alias-brand-primary); font-weight: 600; }
      .fs-chart { display: block; max-width: 100%; margin: 14px 0 4px; border: 1px solid var(--dsw-alias-border-l1); border-radius: 8px; background: #fff; }
      .fs-table { width: 100%; border-collapse: collapse; font-size: 13px; }
      .fs-table th, .fs-table td { padding: 8px 10px; text-align: left; white-space: nowrap; border-bottom: 1px solid var(--dsw-alias-border-l1); }
      .fs-table th { color: var(--dsw-alias-label-secondary); font-weight: 600; }
      .fs-table th.fs-th { cursor: pointer; user-select: none; }
      .fs-table th.fs-th:hover { color: var(--dsw-alias-label-primary); }
      .fs-table tbody tr.fs-click { cursor: pointer; }
      .fs-table tbody tr:hover { background: var(--dsw-alias-bg-layer-1); }
      .fs-table tbody tr.fs-tr-pinned td { background: var(--dsw-alias-bg-layer-1); font-weight: 600; }
      .fs-table tbody tr.fs-tr-pinned td:first-child { color: var(--dsw-alias-brand-primary); }
      .fs-num { text-align: right; }
      .fs-sort-ind { color: var(--dsw-alias-brand-primary); margin-left: 4px; }
      .fs-empty { margin-top: 12px; font-size: 13px; color: var(--dsw-alias-label-secondary); }
      .fs-pair { color: var(--dsw-alias-brand-primary); font-weight: 600; }
      .fs-miss { color: var(--dsw-alias-label-secondary); }
      .fs-hint { margin-top: 8px; font-size: 12px; color: var(--dsw-alias-label-secondary); }
      .fs-pin-card { margin-top: 16px; padding: 14px 16px; border: 1px solid var(--dsw-alias-brand-primary); border-radius: 10px; background: var(--dsw-alias-bg-layer-1); }
      .fs-pin-title { display: flex; align-items: center; gap: 8px; margin: 0 0 10px; font-size: 15px; font-weight: 600; }
      .fs-pin-badge { padding: 1px 8px; border-radius: 999px; background: var(--dsw-alias-brand-primary); color: #fff; font-size: 11px; font-weight: 600; }
      .fs-kv { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 8px 18px; font-size: 13px; }
      .fs-kv-item { display: flex; gap: 6px; }
      .fs-kv-label { color: var(--dsw-alias-label-secondary); }
      .fs-kv-value { font-weight: 500; }
      .fs-history { margin-top: 26px; }
      .fs-history-head { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
      .fs-history-title { font-size: 15px; font-weight: 600; margin: 0; }
      .fs-history-list { list-style: none; margin: 0; padding: 0; border: 1px solid var(--dsw-alias-border-l1); border-radius: 10px; overflow: hidden; }
      .fs-history-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-bottom: 1px solid var(--dsw-alias-border-l1); font-size: 13px; }
      .fs-history-item:last-child { border-bottom: none; }
      .fs-history-item:hover { background: var(--dsw-alias-bg-layer-1); }
      .fs-history-ts { color: var(--dsw-alias-label-secondary); min-width: 92px; }
      .fs-history-main { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .fs-history-pin { color: var(--dsw-alias-brand-primary); font-weight: 600; }
      .fs-tabs { display: inline-flex; gap: 4px; padding: 4px; margin: 0 0 18px; border: 1px solid var(--dsw-alias-border-l1); border-radius: 10px; background: var(--dsw-alias-bg-layer-1); }
      .fs-tab { height: 32px; padding: 0 16px; border: none; border-radius: 7px; background: transparent; color: var(--dsw-alias-label-secondary); font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit; }
      .fs-tab-active { background: color-mix(in srgb, var(--dsw-alias-brand-primary) 25%, transparent); color: var(--dsw-alias-brand-primary); }
      a.fs-btn { display: inline-flex; align-items: center; justify-content: center; text-decoration: none; box-sizing: border-box; }
      .fs-file { font-size: 13px; color: var(--dsw-alias-label-secondary); }
      .fs-bulk-file { font-size: 13px; color: var(--dsw-alias-label-secondary); }
      .fs-bulk-preview { margin-top: 12px; font-size: 13px; }
      .fs-bulk { border: 1px solid var(--dsw-alias-border-l1); border-radius: 10px; padding: 12px 14px; background: var(--dsw-alias-bg-layer-1); }
      .fs-bulk-summary { cursor: pointer; font-size: 14px; font-weight: 600; color: var(--dsw-alias-brand-primary); }
      .fs-bulk-body { margin-top: 12px; overflow-x: auto; }
      .fs-bulk-err td { color: var(--dsw-alias-state-error-primary); }
      .fs-history-group { border-bottom: 1px solid var(--dsw-alias-border-l1); }
      .fs-history-group-title { cursor: pointer; padding: 8px 12px; font-size: 13px; font-weight: 600; color: var(--dsw-alias-label-primary); }
      .fs-history-sublist { list-style: none; margin: 0; padding: 0; border-top: 1px solid var(--dsw-alias-border-l1); }
      .fs-history-file { color: var(--dsw-alias-label-secondary); }
      .fs-history-divider { height: 8px; background: var(--dsw-alias-bg-layer-1); border-top: 1px solid var(--dsw-alias-border-l2); border-bottom: 1px solid var(--dsw-alias-border-l2); }
    `;

    function field(id, label, node) {
      return h('div', { className: 'fs-field' },
        h('label', { className: 'fs-label', htmlFor: id }, label),
        node,
      );
    }

    function numInput(id, value, onChange, step) {
      return h('input', {
        id, className: 'fs-input', type: 'number', min: '0', step: step || 'any',
        value, onChange: (e) => onChange(e.target.value),
        onKeyDown: (e) => { if (e.key === 'Enter') window.__fsRun && window.__fsRun(); },
      });
    }

    function textInput(id, value, onChange, wide) {
      return h('input', {
        id, className: 'fs-input' + (wide ? ' fs-input-wide' : ''), type: 'text',
        value, onChange: (e) => onChange(e.target.value),
        onKeyDown: (e) => { if (e.key === 'Enter') window.__fsRun && window.__fsRun(); },
      });
    }

    const THROTTLE_COLUMNS = [
      { key: 'model', label: 'Модель', numeric: false },
      { key: 'work_point', label: 'Рабочая точка (Q/P)', numeric: true },
      { key: 'max_n', label: 'n, об/мин', numeric: true },
      { key: 'd_reg_pa', label: 'ΔP, Па', numeric: true },
      { key: 'eta_req', label: 'КПД, %', numeric: true },
      { key: 'motor', label: 'Двигатель', numeric: false },
      { key: 'n_kw', label: 'N, кВт', numeric: true },
      { key: 'noise_body_dba', label: 'Шум, дБА', numeric: true },
    ];

    const VFD_COLUMNS = [
      { key: 'model', label: 'Модель', numeric: false },
      { key: 'work_point', label: 'Рабочая точка (Q/P)', numeric: true },
      { key: 'f_hz', label: 'f, Гц', numeric: true },
      { key: 'n_rpm', label: 'n, об/мин', numeric: true },
      { key: 'eta_req', label: 'КПД, %', numeric: true },
      { key: 'motor', label: 'Двигатель', numeric: false },
      { key: 'vfd', label: 'ЧРП', numeric: false },
      { key: 'n_in_w', label: 'N вх, кВт', numeric: true },
    ];

    const COMPARE_COLUMNS = [
      { key: 'model', label: 'Вентилятор', numeric: false },
      { key: 'mode', label: 'Режим', numeric: false },
      { key: 'work_point', label: 'Рабочая точка (Q/P)', numeric: true },
      { key: 'd_reg_pa', label: 'ΔP, Па', numeric: true },
      { key: 'f_hz', label: 'f, Гц', numeric: true },
      { key: 'motor', label: 'Двигатель', numeric: false },
      { key: 'vfd', label: 'ЧРП', numeric: false },
    ];

    // ------------------------------------------------------------------
    // Универсальная таблица с сортировкой, пин-выделением и кликом по строке.
    // ------------------------------------------------------------------
    function Table(props) {
      const { columns, rows, sort, onSort, cell, getter, onRowClick, pinnedModel, pinnedKey } = props;
      const sorted = sort && sort.key
        ? rows.slice().sort((a, b) => compareGeneric(a, b, sort.key, sort.dir, getter))
        : rows;
      return h('table', { className: 'fs-table' },
        h('thead', null,
          h('tr', null, columns.map((c) =>
            h('th', {
              key: c.key,
              className: (c.numeric ? 'fs-num' : '') + ' fs-th',
              onClick: () => onSort({
                key: c.key,
                dir: (sort && sort.key === c.key && sort.dir === 'asc') ? 'desc' : 'asc',
              }),
            },
              c.label,
              sort && sort.key === c.key
                ? h('span', { className: 'fs-sort-ind' }, sort.dir === 'asc' ? '↑' : '↓')
                : null,
            ),
          )),
        ),
        h('tbody', null, sorted.map((r) => {
          const rawVfd = getter(r, 'vfd');
          const isPinned = pinnedKey ? (r.key === pinnedKey) : (pinnedModel && r.model === pinnedModel);
          return h('tr', {
            key: r.key || r.model,
            className: (onRowClick ? 'fs-click ' : '') + (isPinned ? 'fs-tr-pinned' : ''),
            onClick: onRowClick ? () => onRowClick(r) : undefined,
            title: onRowClick ? 'Зафиксировать вентилятор' : undefined,
          },
            columns.map((c) => {
              const text = cell(r, c.key);
              let cls = c.numeric ? 'fs-num' : '';
              if (c.key === 'vfd') cls = rawVfd ? 'fs-pair' : 'fs-miss';
              return h('td', { key: c.key, className: cls }, text);
            }),
          );
        })),
      );
    }

    // ------------------------------------------------------------------
    // Карточка зафиксированного вентилятора.
    // ------------------------------------------------------------------
    function PinCard(props) {
      const { pinned, modeLabel } = props;
      if (!pinned) return null;
      const t = pinned.t && pinned.t.passed ? pinned.t : null;
      const v = pinned.v && pinned.v.passed ? pinned.v : null;
      const motorT = (t && t.motor) || {};
      const motorV = (v && v.motor) || {};
      const vfd = (v && v.vfd) || {};
      const source = v || t || {};

      const kv = (label, value) => h('div', { className: 'fs-kv-item' },
        h('span', { className: 'fs-kv-label' }, label + ':'),
        h('span', { className: 'fs-kv-value' }, value),
      );

      const items = [];
      items.push(kv('Серия', source.series || '—'));
      if (source.dn != null) items.push(kv('DN', fmt(source.dn, 0)));
      if (source.d_over_dn != null) items.push(kv('D/DN', fmt(source.d_over_dn, 3)));
      items.push(kv('n max, об/мин', fmt(source.max_n, 0)));
      if (t) {
        items.push(kv('ΔP (дроссель), Па', fmt(t.d_reg_pa, 1)));
        items.push(kv('КПД (дроссель), %', t.eta_req != null ? fmt(t.eta_req * 100, 1) : '—'));
        items.push(kv('Двигатель (дроссель)', (motorT.name || '—') + (motorT.n_kw != null ? ' · ' + fmt(motorT.n_kw, 1) + ' кВт' : '')));
      }
      if (v) {
        items.push(kv('f (ЧРП), Гц', fmt(v.f_hz, 2)));
        items.push(kv('n (ЧРП), об/мин', fmt(v.n_rpm, 0)));
        items.push(kv('КПД (ЧРП), %', v.eta_req != null ? fmt(v.eta_req * 100, 1) : '—'));
        items.push(kv('Двигатель (ЧРП)', (motorV.name || '—') + (motorV.n_kw != null ? ' · ' + fmt(motorV.n_kw, 1) + ' кВт' : '')));
        items.push(kv('ЧРП', vfd.model || '—'));
        items.push(kv('N вх, кВт', fmt(v.n_in_w / 1000, 2)));
      }
      items.push(kv('Шум, дБ(А)', source.noise_body_dba != null ? fmt(source.noise_body_dba, 0) : '—'));
      items.push(kv('Масса, кг', source.mass != null ? fmt(source.mass, 1) : '—'));
      items.push(kv('Габариты', fmtDims(source.dims)));
      items.push(kv('Исполнения', fmtList(source.executions)));

      return h('div', { className: 'fs-pin-card' },
        h('div', { className: 'fs-pin-title' },
          h('span', null, source.model),
          h('span', { className: 'fs-pin-badge' }, modeLabel),
        ),
        h('div', { className: 'fs-kv' }, items),
      );
    }

    // ------------------------------------------------------------------
    // Блок одного режима (сводка + график + таблица).
    // ------------------------------------------------------------------
    function ResultBlock(props) {
      const { result, modeKey, title, sort, onSort, onPin, pinnedModel } = props;
      const columns = modeKey === 'VFD' ? VFD_COLUMNS : THROTTLE_COLUMNS;
      const results = result && Array.isArray(result.results) ? result.results : [];
      const passed = results.filter((r) => r && r.passed);
      const summary = result && result.summary;

      function bestLine() {
        if (!summary || !summary.best_model) return null;
        if (modeKey === 'VFD') {
          const best = passed[0];
          return h('span', null,
            '. Лучший: ', h('b', null, summary.best_model),
            best && best.f_hz != null ? h('span', null, ' (f = ', h('b', null, fmt(best.f_hz, 2)), ' Гц)') : null,
          );
        }
        return h('span', null,
          '. Лучший: ', h('b', null, summary.best_model),
          summary.best_d_reg_pa != null ? h('span', null, ' (ΔP = ', h('b', null, fmt(summary.best_d_reg_pa, 1)), ' Па)') : null,
        );
      }

      return h('div', { className: 'fs-block' },
        h('h3', { className: 'fs-block-title' }, title),
        summary && h('div', { className: 'fs-summary' },
          'Прошло: ', h('b', null, String(summary.passed)), ' из ', String(summary.total), bestLine(),
        ),
        result && result.chart_png_base64 && h('img', {
          className: 'fs-chart',
          src: 'data:image/png;base64,' + result.chart_png_base64,
          alt: title,
        }),
        result && passed.length === 0 && h('div', { className: 'fs-empty' }, 'Нет подходящих вентиляторов.'),
        passed.length > 0 && h('div', null,
          h(Table, {
            columns, rows: passed, sort, onSort, cell: cellText, getter: sortValue,
            onRowClick: onPin ? (r) => onPin({
              model: r.model, mode: modeKey,
              t: modeKey === 'THROTTLE' ? r : null,
              v: modeKey === 'VFD' ? r : null,
            }) : null,
            pinnedModel,
          }),
          onPin && h('div', { className: 'fs-hint' }, 'Кликните по строке, чтобы зафиксировать вентилятор.'),
        ),
      );
    }

    // ------------------------------------------------------------------
    // Блок сравнения (общая сводка + общий график + общая таблица).
    // ------------------------------------------------------------------
    function CompareBlock(props) {
      const { compare, sort, onSort, onPin, pinnedModel, pinned } = props;
      const t = compare && compare.throttle;
      const v = compare && compare.vfd;

      const tMap = {}, vMap = {}, models = [], seen = {};
      if (t && v) {
        (t.results || []).forEach((r) => { tMap[r.model] = r; });
        (v.results || []).forEach((r) => { vMap[r.model] = r; });
        (t.results || []).forEach((r) => { if (r.passed && !seen[r.model]) { seen[r.model] = 1; models.push(r.model); } });
        (v.results || []).forEach((r) => { if (r.passed && !seen[r.model]) { seen[r.model] = 1; models.push(r.model); } });
      }

      // одна строка — один вариант вентилятора (отдельно дроссель и ЧРП)
      const rows = [];
      models.forEach((m) => {
        const tr = tMap[m];
        const vr = vMap[m];
        if (tr && tr.passed) rows.push({ key: m + '|T', model: m, mode: 'THROTTLE', t: tr, v: null });
        if (vr && vr.passed) rows.push({ key: m + '|V', model: m, mode: 'VFD', t: null, v: vr });
      });
      const pinnedKey = pinned
        ? (pinned.t ? pinned.model + '|T' : pinned.v ? pinned.model + '|V' : null)
        : null;

      return h('div', { className: 'fs-block' },
        h('h3', { className: 'fs-block-title' }, 'Сравнение ЧРП и дорегулирования'),
        t && v && h('div', { className: 'fs-summary' },
          'Дроссельное: ', h('b', null, String(t.summary.passed)), ' из ', String(t.summary.total),
          t.summary.best_model ? h('span', null, ' (лучший ', h('b', null, t.summary.best_model), ')') : null,
          ' · ЧРП: ', h('b', null, String(v.summary.passed)), ' из ', String(v.summary.total),
          v.summary.best_model ? h('span', null, ' (лучший ', h('b', null, v.summary.best_model), ')') : null,
        ),
        compare && compare.chart_png_base64 && h('img', {
          className: 'fs-chart',
          src: 'data:image/png;base64,' + compare.chart_png_base64,
          alt: 'Сравнение',
        }),
        rows.length > 0 && h('div', null,
          h(Table, {
            columns: COMPARE_COLUMNS, rows, sort, onSort, cell: compareCellText, getter: compareSortValue,
            onRowClick: onPin ? (r) => onPin({
              model: r.model, mode: 'COMPARE',
              t: r.mode === 'THROTTLE' ? r.t : null,
              v: r.mode === 'VFD' ? r.v : null,
            }) : null,
            pinnedModel,
            pinnedKey,
          }),
          onPin && h('div', { className: 'fs-hint' }, 'Кликните по строке, чтобы зафиксировать вентилятор.'),
        ),
      );
    }

    // ------------------------------------------------------------------
    // Массовый подбор: сворачиваемый блок с именем файла.
    // ------------------------------------------------------------------
    function bulkRegText(row) {
      const b = row.best;
      if (!b) return 'Нет подходящих';
      if (row.regulation_mode === 'VFD') return 'f = ' + fmt(b.f_hz, 2) + ' Гц';
      return 'ΔP = ' + fmt(b.d_reg_pa, 1) + ' Па';
    }

    function bulkModeLabel(mode) {
      return mode === 'VFD' ? 'ЧРП' : 'Дроссель';
    }

    function BulkBlock(props) {
      const { bulkResult } = props;
      if (!bulkResult) return null;
      const rows = bulkResult.rows || [];
      const noMatch = rows.filter((r) => r.ok && !r.best).length;
      const errCount = rows.filter((r) => !r.ok).length;
      const title = (bulkResult.fileName || 'CSV') + ' · ' + bulkResult.count + ' точек · ' +
        bulkResult.passed + ' прошло' +
        (noMatch ? ' · ' + noMatch + ' без подходящих' : '') +
        (errCount ? ' · ' + errCount + ' ошибок' : '');

      const th = (label, numeric) => h('th', { key: label, className: numeric ? 'fs-num' : '' }, label);

      return h('details', { className: 'fs-block fs-bulk', open: true },
        h('summary', { className: 'fs-bulk-summary' }, title),
        h('div', { className: 'fs-bulk-body' },
          h('table', { className: 'fs-table' },
            h('thead', null, h('tr', null,
              th('№', true),
              th('Система / Комментарий', false),
              th('Q, м³/ч', true),
              th('P, Па', true),
              th('Режим', false),
              th('Вентилятор', false),
              th('Рабочая точка (Q/P)', true),
              th('ΔP / f', false),
              th('Двигатель', false),
              th('ЧРП', false),
            )),
            h('tbody', null, rows.map((r) => {
              if (!r.ok) {
                return h('tr', { key: r.index, className: 'fs-bulk-err' },
                  h('td', { className: 'fs-num' }, String(r.index)),
                  h('td', { colSpan: 9 }, 'Ошибка: ' + ((r.error && r.error.message) || 'неизвестная')),
                );
              }
              const b = r.best;
              const sys = [r.system, r.comment].filter(Boolean).join(' — ') || '—';
              const motor = b && b.motor ? (b.motor.name || '—') : '—';
              const vfd = b && b.vfd ? (b.vfd.model || '—') : '—';
              return h('tr', { key: r.index },
                h('td', { className: 'fs-num' }, String(r.index)),
                h('td', null, sys),
                h('td', { className: 'fs-num' }, fmt(r.q_req, 0)),
                h('td', { className: 'fs-num' }, fmt(r.p_req, 0)),
                h('td', null, bulkModeLabel(r.regulation_mode)),
                h('td', null, b ? b.model : h('span', { className: 'fs-miss' }, 'Нет подходящих')),
                h('td', { className: 'fs-num' }, b ? workPointText(b) : '—'),
                h('td', null, bulkRegText(r)),
                h('td', null, motor),
                h('td', null, vfd),
              );
            })),
          ),
        ),
      );
    }

    // ------------------------------------------------------------------
    // Панель подбора (main, key = PANEL_ID).
    // ------------------------------------------------------------------
    function FanPanel() {
      const [q, setQ] = useState('7500');
      const [p, setP] = useState('700');
      const [pt, setPt] = useState('FULL');
      const [mode, setMode] = useState('THROTTLE');
      const [dReg, setDReg] = useState('1500');
      const [tAir, setTAir] = useState('20');
      const [fMin, setFMin] = useState('20');
      const [fMax, setFMax] = useState('60');
      const [systemName, setSystemName] = useState('');
      const [comment, setComment] = useState('');
      const [singleThrottle, setSingleThrottle] = useState(null);
      const [singleVfd, setSingleVfd] = useState(null);
      const [compare, setCompare] = useState(null);
      const [loading, setLoading] = useState(false);
      const [error, setError] = useState(null);
      const [sort, setSort] = useState({ key: null, dir: 'asc' });
      const [pinned, setPinned] = useState(null);
      const [history, setHistory] = useState([]);
      const [selectionType, setSelectionType] = useState('single');
      const [bulkFile, setBulkFile] = useState(null);
      const [bulkPreview, setBulkPreview] = useState(null);
      const [bulkResult, setBulkResult] = useState(null);
      const editOriginRef = useRef(null);

      useEffect(() => {
        let cancelled = false;
        fetchHistoryList().then((items) => { if (!cancelled) setHistory(items); });
        return () => { cancelled = true; };
      }, []);

      function buildQuery(regMode) {
        return {
          q_req: Number(q),
          p_req: Number(p),
          pressure_type: pt,
          regulation_mode: regMode,
          d_reg_max: Number(dReg) || 1500,
          t_air: Number(tAir) || 20,
          freq_min_hz: Number(fMin) || 20,
          freq_max_hz: Number(fMax) || 60,
        };
      }

      async function fetchJson(path, payload) {
        const res = await fetch(API_BASE + path, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error((data && data.error && data.error.message) || 'ошибка сервера');
        }
        return data;
      }

      // ---- автосохранение в «Выполненные подборы» ----
      function currentParams() {
        return {
          q: Number(q), p: Number(p),
          pt: pt, mode: mode,
          dRegMax: Number(dReg) || 1500,
          tAir: Number(tAir) || 20,
          fMin: Number(fMin) || 20,
          fMax: Number(fMax) || 60,
          system: systemName || '', comment: comment || '',
        };
      }

      function singleEntry(model, dRegPa, fHz, motor, vfd, params) {
        const P = params || currentParams();
        return {
          id: String(Date.now()) + Math.random().toString(16).slice(2, 6),
          ts: Date.now(),
          kind: 'single',
          q: P.q, p: P.p,
          pressure_type: P.pt, mode: P.mode,
          d_reg_max: P.dRegMax,
          t_air: P.tAir,
          freq_min_hz: P.fMin,
          freq_max_hz: P.fMax,
          system: P.system, comment: P.comment,
          pinnedModel: model || null,
          d_reg_pa: dRegPa != null ? dRegPa : null,
          f_hz: fHz != null ? fHz : null,
          motor: motor || null, vfd: vfd || null,
        };
      }

      function isSameSingle(e, entry) {
        return e.kind === 'single' &&
          e.q === entry.q && e.p === entry.p &&
          (e.pressure_type || 'FULL') === entry.pressure_type &&
          (e.mode || 'THROTTLE') === entry.mode &&
          (e.d_reg_max != null ? e.d_reg_max : 1500) === entry.d_reg_max &&
          (e.t_air != null ? e.t_air : 20) === entry.t_air &&
          (e.freq_min_hz != null ? e.freq_min_hz : 20) === entry.freq_min_hz &&
          (e.freq_max_hz != null ? e.freq_max_hz : 60) === entry.freq_max_hz &&
          (e.system || '') === entry.system &&
          (e.comment || '') === entry.comment;
      }

      function upsertEntry(entry) {
        const same = history.find((e) => isSameSingle(e, entry));
        if (same) { entry.id = same.id; entry.ts = same.ts; }
        const next = [entry].concat(history.filter((e) => e.id !== entry.id)).slice(0, HISTORY_CAP);
        setHistory(next);
        postHistory(entry).then((items) => { if (items) setHistory(items); });
      }

      function bestEntryValues(res, modeKey) {
        const best = (res && res.results || []).find((r) => r && r.passed) || null;
        if (!best) return { model: null, d_reg_pa: null, f_hz: null, motor: null, vfd: null, best: null };
        return {
          model: best.model,
          d_reg_pa: modeKey === 'THROTTLE' ? (best.d_reg_pa != null ? best.d_reg_pa : null) : null,
          f_hz: modeKey === 'VFD' ? (best.f_hz != null ? best.f_hz : null) : null,
          motor: (best.motor) || null,
          vfd: modeKey === 'VFD' ? (best.vfd || null) : null,
          best: best,
        };
      }

      function compareBestFromResult(res) {
        const t = res && res.throttle;
        const v = res && res.vfd;
        const tBest = (t && t.results || []).find((r) => r && r.passed) || null;
        const vBest = (v && v.results || []).find((r) => r && r.passed) || null;
        if (tBest) {
          // выбирается один вариант — по умолчанию дроссельный (не оба сразу)
          return {
            model: tBest.model,
            d_reg_pa: tBest.d_reg_pa != null ? tBest.d_reg_pa : null,
            f_hz: null,
            motor: (tBest.motor) || null,
            vfd: null,
            t: tBest, v: null,
          };
        }
        if (vBest) {
          return {
            model: vBest.model,
            d_reg_pa: null,
            f_hz: vBest.f_hz != null ? vBest.f_hz : null,
            motor: (vBest.motor) || null,
            vfd: (vBest.vfd || null),
            t: null, v: vBest,
          };
        }
        return { model: null, d_reg_pa: null, f_hz: null, motor: null, vfd: null, t: null, v: null };
      }

      function saveSelection(model, dRegPa, fHz, motor, vfd, params) {
        const P = params || currentParams();
        const origin = editOriginRef.current;
        if (origin && origin.kind === 'bulk') {
          const entry = Object.assign({}, origin, {
            q: P.q, p: P.p,
            pressure_type: P.pt, mode: P.mode,
            d_reg_max: P.dRegMax, t_air: P.tAir,
            freq_min_hz: P.fMin, freq_max_hz: P.fMax,
            system: P.system, comment: P.comment,
            pinnedModel: model || null,
            d_reg_pa: dRegPa != null ? dRegPa : null,
            f_hz: fHz != null ? fHz : null,
            motor: motor || null, vfd: vfd || null,
          });
          const next = history.map((e) => (e.id === entry.id ? entry : e));
          setHistory(next);
          postHistory(entry).then((items) => { if (items) setHistory(items); });
          return;
        }
        upsertEntry(singleEntry(model, dRegPa, fHz, motor, vfd, P));
      }

      async function doRun(query, modeKey, saveParams) {
        setLoading(true);
        setError(null);
        setSingleThrottle(null);
        setSingleVfd(null);
        setCompare(null);
        setPinned(null);
        setSort({ key: null, dir: 'asc' });
        try {
          if (modeKey === 'COMPARE') {
            const res = await fetchJson('/compare', query);
            setCompare(res);
            const b = compareBestFromResult(res);
            setPinned(b.model ? { model: b.model, mode: 'COMPARE', t: b.t, v: b.v } : null);
            saveSelection(b.model, b.d_reg_pa, b.f_hz, b.motor, b.vfd, saveParams);
          } else if (modeKey === 'VFD') {
            const res = await fetchJson('/chart', Object.assign({}, query, { regulation_mode: 'VFD' }));
            setSingleVfd(res);
            const bv = bestEntryValues(res, 'VFD');
            setPinned(bv.best ? { model: bv.best.model, mode: 'VFD', t: null, v: bv.best } : null);
            saveSelection(bv.model, bv.d_reg_pa, bv.f_hz, bv.motor, bv.vfd, saveParams);
          } else {
            const res = await fetchJson('/chart', Object.assign({}, query, { regulation_mode: 'THROTTLE' }));
            setSingleThrottle(res);
            const bv = bestEntryValues(res, 'THROTTLE');
            setPinned(bv.best ? { model: bv.best.model, mode: 'THROTTLE', t: bv.best, v: null } : null);
            saveSelection(bv.model, bv.d_reg_pa, bv.f_hz, bv.motor, bv.vfd, saveParams);
          }
        } catch (e) {
          setError('Не удалось выполнить подбор. ' + (e && e.message ? e.message : ''));
        } finally {
          setLoading(false);
        }
      }

      function run() {
        if (selectionType !== 'single') return;
        const qNum = Number(q);
        const pNum = Number(p);
        if (!Number.isFinite(qNum) || qNum <= 0 || !Number.isFinite(pNum) || pNum <= 0) {
          setError('Введите положительные числа для расхода и давления.');
          return;
        }
        const needsVfd = mode === 'VFD' || mode === 'COMPARE';
        const fMinNum = Number(fMin);
        const fMaxNum = Number(fMax);
        if (needsVfd && (!Number.isFinite(fMinNum) || !Number.isFinite(fMaxNum) || fMaxNum <= fMinNum)) {
          setError('Задайте корректный диапазон частоты: f_min < f_max.');
          return;
        }
        doRun(buildQuery(mode), mode);
      }

      window.__fsRun = run;

      function resetToDefaults() {
        setQ('7500');
        setP('700');
        setPt('FULL');
        setMode('THROTTLE');
        setDReg('1500');
        setTAir('20');
        setFMin('20');
        setFMax('60');
        setSystemName('');
        setComment('');
        setSingleThrottle(null);
        setSingleVfd(null);
        setCompare(null);
        setLoading(false);
        setError(null);
        setSort({ key: null, dir: 'asc' });
        setPinned(null);
        setBulkFile(null);
        setBulkPreview(null);
        setBulkResult(null);
        editOriginRef.current = null;
      }

      function switchType(t) {
        setSelectionType(t);
        setError(null);
        setPinned(null);
        setSort({ key: null, dir: 'asc' });
        setSingleThrottle(null);
        setSingleVfd(null);
        setCompare(null);
        setBulkResult(null);
        editOriginRef.current = null;
      }

      function pinRow(pinnedRec) {
        setPinned(pinnedRec);
        if (mode === 'COMPARE') {
          const t = pinnedRec.t && pinnedRec.t.passed ? pinnedRec.t : null;
          const v = pinnedRec.v && pinnedRec.v.passed ? pinnedRec.v : null;
          const src = v || t;
          saveSelection(
            pinnedRec.model,
            t ? (t.d_reg_pa != null ? t.d_reg_pa : null) : null,
            v ? (v.f_hz != null ? v.f_hz : null) : null,
            (src && src.motor) || null,
            v ? (v.vfd || null) : null,
          );
        } else {
          const src = mode === 'VFD' ? pinnedRec.v : pinnedRec.t;
          saveSelection(
            pinnedRec.model,
            mode === 'THROTTLE' && src ? (src.d_reg_pa != null ? src.d_reg_pa : null) : null,
            mode === 'VFD' && src ? (src.f_hz != null ? src.f_hz : null) : null,
            src ? (src.motor || null) : null,
            mode === 'VFD' && src ? (src.vfd || null) : null,
          );
        }
      }

      function restoreEntry(entry) {
        editOriginRef.current = entry;
        setSelectionType('single');
        setQ(String(entry.q));
        setP(String(entry.p));
        setPt(entry.pressure_type || 'FULL');
        setMode(entry.mode || 'THROTTLE');
        setDReg(String(entry.d_reg_max != null ? entry.d_reg_max : 1500));
        setTAir(String(entry.t_air != null ? entry.t_air : 20));
        setFMin(String(entry.freq_min_hz != null ? entry.freq_min_hz : 20));
        setFMax(String(entry.freq_max_hz != null ? entry.freq_max_hz : 60));
        setSystemName(entry.system || '');
        setComment(entry.comment || '');
        doRun({
          q_req: entry.q,
          p_req: entry.p,
          pressure_type: entry.pressure_type || 'FULL',
          regulation_mode: entry.mode || 'THROTTLE',
          d_reg_max: entry.d_reg_max != null ? entry.d_reg_max : 1500,
          t_air: entry.t_air != null ? entry.t_air : 20,
          freq_min_hz: entry.freq_min_hz != null ? entry.freq_min_hz : 20,
          freq_max_hz: entry.freq_max_hz != null ? entry.freq_max_hz : 60,
        }, entry.mode || 'THROTTLE', {
          q: entry.q,
          p: entry.p,
          pt: entry.pressure_type || 'FULL',
          mode: entry.mode || 'THROTTLE',
          dRegMax: entry.d_reg_max != null ? entry.d_reg_max : 1500,
          tAir: entry.t_air != null ? entry.t_air : 20,
          fMin: entry.freq_min_hz != null ? entry.freq_min_hz : 20,
          fMax: entry.freq_max_hz != null ? entry.freq_max_hz : 60,
          system: entry.system || '', comment: entry.comment || '',
        });
      }

      function deleteEntry(id) {
        const next = history.filter((e) => e.id !== id);
        setHistory(next);
        deleteHistory(id).then((items) => { if (items) setHistory(items); });
      }

      function clearHistory() {
        setHistory([]);
        deleteHistory(null).then((items) => { if (items) setHistory(items); });
      }

      // ---- массовый подбор ----
      async function onBulkFileChange(e) {
        const file = e.target.files && e.target.files[0];
        if (!file) return;
        let base64;
        try {
          base64 = await readFileAsBase64(file);
        } catch (err) {
          setError('Не удалось прочитать файл. ' + (err && err.message ? err.message : ''));
          return;
        }
        setBulkFile({ name: file.name, base64 });
        setBulkPreview(null);
        setBulkResult(null);
        setPinned(null);
        setError(null);
        setLoading(true);
        try {
          const preview = await fetchJson('/batch/parse', { fileName: file.name, csvBase64: base64 });
          if (preview && preview.error) {
            setError('Ошибка чтения файла: ' + preview.error.message);
            setBulkPreview(null);
          } else {
            setBulkPreview(preview);
          }
        } catch (err) {
          setError('Не удалось прочитать файл. ' + (err && err.message ? err.message : ''));
        } finally {
          setLoading(false);
        }
      }

      async function runBulk() {
        if (!bulkFile) { setError('Сначала загрузите CSV-файл.'); return; }
        setLoading(true);
        setError(null);
        setBulkResult(null);
        setPinned(null);
        try {
          const res = await fetchJson('/batch', { fileName: bulkFile.name, csvBase64: bulkFile.base64 });
          if (res && res.error) {
            setError('Ошибка массового подбора: ' + res.error.message);
            return;
          }
          setBulkResult(res);
          const batchId = 'b-' + Date.now() + Math.random().toString(16).slice(2, 6);
          const entries = [];
          (res.rows || []).forEach((row) => {
            if (!row.ok) return;
            const best = row.best || null;
            entries.push({
              id: String(Date.now()) + Math.random().toString(16).slice(2, 6),
              ts: Date.now(),
              kind: 'bulk',
              batchId,
              fileName: res.fileName || bulkFile.name,
              row: row.index,
              q: row.q_req, p: row.p_req,
              pressure_type: row.pressure_type || 'FULL',
              mode: row.regulation_mode || 'THROTTLE',
              d_reg_max: row.d_reg_max != null ? row.d_reg_max : 1500,
              t_air: row.t_air != null ? row.t_air : 20,
              freq_min_hz: row.freq_min_hz != null ? row.freq_min_hz : 20,
              freq_max_hz: row.freq_max_hz != null ? row.freq_max_hz : 60,
              system: row.system || '', comment: row.comment || '',
              pinnedModel: best ? best.model : null,
              d_reg_pa: best ? (best.d_reg_pa != null ? best.d_reg_pa : null) : null,
              f_hz: best ? (best.f_hz != null ? best.f_hz : null) : null,
              motor: best ? (best.motor || null) : null,
              vfd: best ? (best.vfd || null) : null,
            });
          });
          postHistoryBatch(entries, res.fileName || bulkFile.name).then((items) => { if (items) setHistory(items); });
        } catch (err) {
          setError('Не удалось выполнить массовый подбор. ' + (err && err.message ? err.message : ''));
        } finally {
          setLoading(false);
        }
      }

      const isVfd = mode === 'VFD';
      const isCompare = mode === 'COMPARE';
      const showDreg = mode !== 'VFD';
      const showFreq = mode === 'VFD' || isCompare;
      const pinnedModel = pinned ? pinned.model : null;
      const modeLabel = modeLabelText(mode);
      const hasResult = !!(singleThrottle || singleVfd || compare || bulkResult);

      function renderBody() {
        if (selectionType === 'bulk') return h(BulkBlock, { bulkResult });
        if (isCompare) return h(CompareBlock, { compare, sort, onSort: setSort, onPin: pinRow, pinnedModel, pinned });
        if (isVfd) return h(ResultBlock, { result: singleVfd, modeKey: 'VFD', title: 'Частотное регулирование (ЧРП)', sort, onSort: setSort, onPin: pinRow, pinnedModel });
        return h(ResultBlock, { result: singleThrottle, modeKey: 'THROTTLE', title: 'Дроссельное регулирование', sort, onSort: setSort, onPin: pinRow, pinnedModel });
      }

      function historyTitle(e) {
        const ml = modeLabelText(e.mode);
        let reg = '';
        if (!e.pinnedModel) {
          reg = 'Нет подходящих';
        } else if (e.mode === 'THROTTLE') {
          reg = 'ΔP = ' + fmt(e.d_reg_pa, 1) + ' Па';
        } else if (e.mode === 'VFD') {
          reg = 'f = ' + fmt(e.f_hz, 2) + ' Гц';
        } else {
          if (e.d_reg_pa != null) reg = 'ΔP = ' + fmt(e.d_reg_pa, 1) + ' Па';
          else if (e.f_hz != null) reg = 'f = ' + fmt(e.f_hz, 2) + ' Гц';
          else reg = 'Нет подходящих';
        }
        const base = e.q + ' м³/ч / ' + e.p + ' Па · ' + ml + (reg ? ' · ' + reg : '');
        const meta = [e.system, e.comment].filter(Boolean).join(' — ');
        return meta ? meta + ' · ' + base : base;
      }

      function buildHistoryBlocks() {
        const blocks = [];
        const byFile = {};
        history.forEach((e) => {
          if (e.kind === 'bulk') {
            const key = e.fileName || e.batchId || ('batch-' + e.id);
            if (!byFile[key]) byFile[key] = { key, fileName: e.fileName || 'CSV', entries: [], ts: 0 };
            byFile[key].entries.push(e);
            if (e.ts > byFile[key].ts) byFile[key].ts = e.ts;
          } else {
            blocks.push({ type: 'single', single: e, ts: e.ts || 0 });
          }
        });
        Object.keys(byFile).forEach((k) => {
          byFile[k].entries.sort((a, b) => (a.row || 0) - (b.row || 0));
          blocks.push({ type: 'group', group: byFile[k], ts: byFile[k].ts || 0 });
        });
        blocks.sort((a, b) => b.ts - a.ts);
        return blocks;
      }

      function historyItemContent(e) {
        return [
          h('span', { className: 'fs-history-ts', key: 'ts' }, tsLabel(e.ts)),
          h('span', { className: 'fs-history-main', key: 'main' },
            historyTitle(e),
            e.pinnedModel ? h('span', null, ' → ', h('span', { className: 'fs-history-pin' }, e.pinnedModel)) : null,
            e.kind === 'bulk' ? h('span', { className: 'fs-history-file' }, ' · №' + e.row) : null,
          ),
          h('button', { className: 'fs-btn-ghost', type: 'button', key: 'restore', onClick: () => restoreEntry(e) }, 'Восстановить'),
          h('button', { className: 'fs-btn-ghost', type: 'button', key: 'del', onClick: () => deleteEntry(e.id) }, '×'),
        ];
      }

      function renderHistoryBody() {
        const blocks = buildHistoryBlocks();
        if (!blocks.length) {
          return h('div', { className: 'fs-empty' }, 'История пуста. Выполните подбор — результат попадёт сюда автоматически.');
        }
        const items = [];
        blocks.forEach((b, i) => {
          if (i > 0 && blocks[i - 1].type !== b.type) {
            items.push(h('li', { className: 'fs-history-divider', key: 'divider-' + i, 'aria-hidden': true }));
          }
          if (b.type === 'single') {
            items.push(h('li', { className: 'fs-history-item', key: b.single.id }, historyItemContent(b.single)));
          } else {
            const g = b.group;
            items.push(h('li', { className: 'fs-history-group', key: 'g-' + g.key },
              h('details', null,
                h('summary', { className: 'fs-history-group-title' }, '📄 ' + g.fileName + ' · ' + g.entries.length + ' точек'),
                h('ul', { className: 'fs-history-sublist' },
                  g.entries.map((e) => h('li', { className: 'fs-history-item', key: e.id }, historyItemContent(e))),
                ),
              ),
            ));
          }
        });
        return h('ul', { className: 'fs-history-list' }, items);
      }

      return h(
        'div',
        { className: 'fs-panel' },
        h('style', null, CSS),
        h('div', { className: 'fs-inner' },
          h('h2', { className: 'fs-title' }, 'Подбор радиального вентилятора'),
          h('p', { className: 'fs-subtitle' }, 'ВР 86-77 и ВР 280-46 · дроссельное и частотное (ЧРП) регулирование'),

          h('div', { className: 'fs-tabs' },
            h('button', { className: 'fs-tab' + (selectionType === 'single' ? ' fs-tab-active' : ''), type: 'button', onClick: () => switchType('single') }, 'Единичный подбор'),
            h('button', { className: 'fs-tab' + (selectionType === 'bulk' ? ' fs-tab-active' : ''), type: 'button', onClick: () => switchType('bulk') }, 'Массовый подбор'),
          ),

          selectionType === 'single' && h('div', { className: 'fs-form' },
            field('fs-q', 'Расход Q, м³/ч', numInput('fs-q', q, setQ)),
            field('fs-p', 'Давление P, Па', numInput('fs-p', p, setP)),
            field('fs-pt', 'Тип давления', h('select', { id: 'fs-pt', className: 'fs-select', value: pt, onChange: (e) => setPt(e.target.value) },
              h('option', { value: 'FULL' }, 'Полное'),
              h('option', { value: 'STATIC' }, 'Статическое'),
            )),
            field('fs-mode', 'Режим подбора', h('select', {
              id: 'fs-mode', className: 'fs-select', value: mode,
              onChange: (e) => { setMode(e.target.value); setSort({ key: null, dir: 'asc' }); setPinned(null); },
            },
              h('option', { value: 'THROTTLE' }, 'Дроссельное'),
              h('option', { value: 'VFD' }, 'Частотное (ЧРП)'),
              h('option', { value: 'COMPARE' }, 'Сравнение ЧРП и дорегулирования'),
            )),

            showDreg && field('fs-dreg', 'Дорегулирование ΔP, Па', numInput('fs-dreg', dReg, setDReg)),
            field('fs-tair', 'Температура, °C', numInput('fs-tair', tAir, setTAir)),

            showFreq && h('div', { className: 'fs-row' },
              field('fs-fmin', 'f мин, Гц', numInput('fs-fmin', fMin, setFMin, '1')),
              field('fs-fmax', 'f макс, Гц', numInput('fs-fmax', fMax, setFMax, '1')),
            ),

            h('button', { className: 'fs-btn', type: 'button', disabled: loading, onClick: run },
              loading ? 'Расчёт…' : 'Рассчитать',
            ),
          ),

          selectionType === 'single' && h('div', { className: 'fs-block fs-info' },
            h('h3', { className: 'fs-block-title' }, 'Информация о подборе'),
            h('div', { className: 'fs-form' },
              field('fs-system', 'Система', textInput('fs-system', systemName, setSystemName, true)),
              field('fs-comment', 'Комментарий', textInput('fs-comment', comment, setComment, true)),
            ),
          ),

          selectionType === 'bulk' && h('div', { className: 'fs-block' },
            h('h3', { className: 'fs-block-title' }, 'Массовый подбор'),
            h('div', { className: 'fs-form' },
              h('a', { className: 'fs-btn', href: API_BASE + '/template.csv', download: 'шаблон_подбора.csv' }, 'Скачать шаблон CSV'),
              h('input', { className: 'fs-file', type: 'file', accept: '.csv,text/csv', onChange: onBulkFileChange }),
              bulkFile ? h('span', { className: 'fs-bulk-file' }, bulkFile.name) : null,
              h('button', { className: 'fs-btn', type: 'button', disabled: loading || !bulkFile, onClick: runBulk },
                loading ? 'Расчёт…' : 'Рассчитать',
              ),
            ),
            bulkPreview && !bulkResult && h('div', { className: 'fs-bulk-preview' },
              h('div', { className: 'fs-summary' },
                'Строк: ', h('b', null, String(bulkPreview.totalRows)), ' · корректных: ', h('b', null, String(bulkPreview.validRows)),
              ),
              (bulkPreview.errors || []).map((er) => h('div', { className: 'fs-error', key: er.row }, 'Строка ' + er.row + ': ' + er.message)),
            ),
          ),

          error && h('div', { className: 'fs-error' }, error),

          renderBody(),

          h(PinCard, { pinned, modeLabel }),

          hasResult && h('div', { className: 'fs-next' },
            h('button', { className: 'fs-btn fs-btn-next', type: 'button', onClick: resetToDefaults },
              '+ Следующий подбор',
            ),
          ),

          h('div', { className: 'fs-history' },
            h('div', { className: 'fs-history-head' },
              h('h3', { className: 'fs-history-title' }, 'Выполненные подборы (' + history.length + ')'),
              history.length > 0 && h('button', { className: 'fs-btn-ghost', type: 'button', onClick: clearHistory }, 'Очистить'),
            ),
            renderHistoryBody(),
          ),
        ),
      );
    }

    return {
      inject: ['slots'],
      apply(ctx) {
        ctx.slots.inject('sidebar.panellist', () =>
          ctx.slots.register(
            { name: 'sidebar.panellist', id: PANEL_ID, order: 20, label: () => 'Подбор вентилятора' },
            FanIcon,
          ),
        );
        ctx.slots.inject('main', () =>
          ctx.slots.register({ name: 'main', key: PANEL_ID }, FanPanel),
        );
      },
    };
  },
});
