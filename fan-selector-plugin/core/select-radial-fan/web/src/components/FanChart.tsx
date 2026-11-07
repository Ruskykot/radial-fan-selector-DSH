import type { FanResult } from "../types";

const PASSED_COLORS = ["#1e78c8", "#e0861e", "#28a060", "#8c46c8"];

export default function FanChart({ result }: { result: FanResult }) {
  const qReq = result.query.q_req;
  const pReq = result.query.p_req;

  const allQ: number[] = [qReq];
  const allP: number[] = [pReq];
  for (const r of result.results) {
    allQ.push(...(r.curve?.q_points ?? []));
    allP.push(...(r.curve?.p_points ?? []));
  }
  const qMin = Math.min(...allQ);
  const qMax = Math.max(...allQ);
  const pMax = (Math.max(...allP) || 1) * 1.1;

  const W = 800, H = 500, ML = 64, MR = 20, MT = 20, MB = 54;
  const pw = W - ML - MR;
  const ph = H - MT - MB;
  const px = (q: number) => ML + ((q - qMin) / (qMax - qMin || 1)) * pw;
  const py = (p: number) => MT + (1 - p / pMax) * ph;

  // Кривая сети P = k·Q²
  const k = qReq > 0 ? pReq / (qReq * qReq) : 0;
  const netPts = Array.from({ length: 80 }, (_, i) => {
    const q = qMin + ((qMax - qMin) * i) / 79;
    return `${px(q).toFixed(1)},${py(k * q * q).toFixed(1)}`;
  }).join(" ");

  let colorIdx = 0;

  return (
    <div style={{ background: "#fff", border: "1px solid #ddd", borderRadius: 8, padding: 16, marginTop: 12 }}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>Характеристики P(Q)</div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", display: "block" }}>
        {/* сетка */}
        {Array.from({ length: 6 }, (_, i) => {
          const fy = i / 5;
          const gy = MT + fy * ph;
          const fx = i / 5;
          const gx = ML + fx * pw;
          return (
            <g key={i}>
              <line x1={ML} y1={gy} x2={W - MR} y2={gy} stroke="#eee" />
              <line x1={gx} y1={MT} x2={gx} y2={H - MB} stroke="#eee" />
              <text x={6} y={gy + 4} fontSize={11} fill="#666">{(pMax * (1 - fy)).toFixed(0)}</text>
              <text x={gx - 14} y={H - MB + 18} fontSize={11} fill="#666">{(qMin + fx * (qMax - qMin)).toFixed(0)}</text>
            </g>
          );
        })}

        {/* оси */}
        <line x1={ML} y1={MT} x2={ML} y2={H - MB} stroke="#333" />
        <line x1={ML} y1={H - MB} x2={W - MR} y2={H - MB} stroke="#333" />
        <text x={10} y={MT + 10} fontSize={13} fill="#333">P, Па</text>
        <text x={W - MR - 70} y={H - MB + 32} fontSize={13} fill="#333">Q, м³/ч</text>

        {/* кривая сети */}
        <polyline points={netPts} fill="none" stroke="#999" strokeDasharray="6 5" strokeWidth={1.5} />

        {/* кривые вентиляторов */}
        {result.results.map((r) => {
          const qp = r.curve?.q_points ?? [];
          const pp = r.curve?.p_points ?? [];
          if (qp.length === 0 || pp.length === 0) return null;
          const pts = qp.map((q, i) => `${px(q).toFixed(1)},${py(pp[i]).toFixed(1)}`).join(" ");
          if (r.passed) {
            const c = PASSED_COLORS[colorIdx++ % PASSED_COLORS.length];
            return <polyline key={r.model} points={pts} fill="none" stroke={c} strokeWidth={2} />;
          }
          return <polyline key={r.model} points={pts} fill="none" stroke="#ddd" strokeDasharray="4 4" strokeWidth={1} />;
        })}

        {/* рабочая точка */}
        <circle cx={px(qReq)} cy={py(pReq)} r={5} fill="#fff" stroke="#e02020" strokeWidth={2.5} />
        <line x1={px(qReq)} y1={py(pReq)} x2={px(qReq)} y2={H - MB} stroke="#e02020" strokeWidth={1} />
        <line x1={ML} y1={py(pReq)} x2={px(qReq)} y2={py(pReq)} stroke="#e02020" strokeWidth={1} />
      </svg>
      <div style={{ fontSize: 12, color: "#666", marginTop: 6 }}>
        Цветные линии — прошедшие; серый пунктир — отсеянные; красная точка — рабочая (Q, P); серый пунктир — кривая сети.
      </div>
    </div>
  );
}
