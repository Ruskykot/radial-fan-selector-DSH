import { useState, type CSSProperties, type FormEvent } from "react";
import type { PressureType, SelectionQuery } from "../types";
import { DN_OPTIONS, RPM_OPTIONS, SERIES_OPTIONS, VALIDATION } from "../config";

interface Props {
  onSubmit: (q: SelectionQuery) => void;
  loading: boolean;
}

const labelStyle: CSSProperties = { display: "block", marginTop: 10, fontWeight: 600 };
const inputStyle: CSSProperties = { width: "100%", boxSizing: "border-box", padding: 6, marginTop: 4 };
const boxStyle: CSSProperties = { border: "1px solid #ddd", borderRadius: 8, background: "#fff", padding: 16 };

export default function FanForm({ onSubmit, loading }: Props) {
  const [q, setQ] = useState("7500");
  const [p, setP] = useState("700");
  const [pressureType, setPressureType] = useState<PressureType>("FULL");
  const [series, setSeries] = useState<string[]>([]);
  const [sizes, setSizes] = useState<number[]>([]);
  const [rpms, setRpms] = useState<number[]>([]);

  const qNum = Number(q);
  const pNum = Number(p);
  const qErr = q !== "" && (Number.isNaN(qNum) || qNum < VALIDATION.q.min || qNum > VALIDATION.q.max);
  const pErr = p !== "" && (Number.isNaN(pNum) || pNum < VALIDATION.p.min || pNum > VALIDATION.p.max);
  const invalid = q === "" || p === "" || qErr || pErr;

  function toggle<T>(arr: T[], set: (v: T[]) => void, value: T) {
    set(arr.includes(value) ? arr.filter((x) => x !== value) : [...arr, value]);
  }

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (invalid) return;
    onSubmit({
      q_req: qNum,
      p_req: pNum,
      pressure_type: pressureType,
      series: series.length ? series : undefined,
      sizes: sizes.length ? sizes : undefined,
      rpms: rpms.length ? rpms : undefined,
    });
  }

  return (
    <form onSubmit={submit} style={boxStyle}>
      <label style={labelStyle}>Расход Q, м³/ч *</label>
      <input style={inputStyle} value={q} onChange={(e) => setQ(e.target.value)} inputMode="decimal" />
      {qErr && <div style={{ color: "#b00020", fontSize: 12 }}>Допустимо {VALIDATION.q.min}–{VALIDATION.q.max}</div>}

      <label style={labelStyle}>Давление P, Па *</label>
      <input style={inputStyle} value={p} onChange={(e) => setP(e.target.value)} inputMode="decimal" />
      {pErr && <div style={{ color: "#b00020", fontSize: 12 }}>Допустимо {VALIDATION.p.min}–{VALIDATION.p.max}</div>}

      <label style={labelStyle}>Тип давления</label>
      <div style={{ marginTop: 4 }}>
        {(["FULL", "STATIC"] as const).map((t) => (
          <label key={t} style={{ display: "block", fontWeight: 400 }}>
            <input type="radio" checked={pressureType === t} onChange={() => setPressureType(t)} />
            {t === "FULL" ? " Полное (рекомендуется)" : " Статическое"}
          </label>
        ))}
      </div>

      <label style={labelStyle}>Серия</label>
      <div style={{ marginTop: 4 }}>
        {SERIES_OPTIONS.map((s) => (
          <label key={s} style={{ display: "block", fontWeight: 400 }}>
            <input type="checkbox" checked={series.includes(s)} onChange={() => toggle(series, setSeries, s)} />
            {" "}{s}
          </label>
        ))}
      </div>

      <label style={labelStyle}>Типоразмер DN</label>
      <div style={{ marginTop: 4, display: "grid", gridTemplateColumns: "1fr 1fr" }}>
        {DN_OPTIONS.map((d) => (
          <label key={d} style={{ fontWeight: 400 }}>
            <input type="checkbox" checked={sizes.includes(d)} onChange={() => toggle(sizes, setSizes, d)} />
            {" "}{d}
          </label>
        ))}
      </div>

      <label style={labelStyle}>Обороты, об/мин</label>
      <div style={{ marginTop: 4, display: "grid", gridTemplateColumns: "1fr 1fr" }}>
        {RPM_OPTIONS.map((r) => (
          <label key={r} style={{ fontWeight: 400 }}>
            <input type="checkbox" checked={rpms.includes(r)} onChange={() => toggle(rpms, setRpms, r)} />
            {" "}{r}
          </label>
        ))}
      </div>

      <button
        type="submit"
        disabled={invalid || loading}
        style={{ marginTop: 16, width: "100%", padding: 10, background: "#1e78c8", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer" }}
      >
        {loading ? "Расчёт…" : "Рассчитать"}
      </button>
      <div style={{ fontSize: 12, color: "#888", marginTop: 8 }}>
        Пустые фильтры = без ограничений.
      </div>
    </form>
  );
}
