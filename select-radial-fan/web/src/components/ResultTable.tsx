import type { CSSProperties } from "react";
import type { FanResult } from "../types";

export default function ResultTable({ result }: { result: FanResult }) {
  const passed = result.results.filter((r) => r.passed);
  const s = result.summary;

  return (
    <div style={{ background: "#fff", border: "1px solid #ddd", borderRadius: 8, padding: 16 }}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>
        {s.best_model ? (
          <>Лучший: {s.best_model} (ΔP = {s.best_d_reg_pa} Па)</>
        ) : (
          <>Подходящих вентиляторов не найдено</>
        )}
        <span style={{ color: "#666", fontWeight: 400 }}>
          {" "}— прошло {s.passed} из {s.total}
        </span>
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>
            <th style={th}>Модель</th>
            <th style={th}>DN</th>
            <th style={th}>D/DN</th>
            <th style={th}>Об/мин</th>
            <th style={th}>ΔP, Па</th>
            <th style={th}>КПД</th>
            <th style={th}>N, кВт</th>
            <th style={th}>Двигатель</th>
          </tr>
        </thead>
        <tbody>
          {passed.map((r) => (
            <tr key={r.model} style={{ borderBottom: "1px solid #eee" }}>
              <td style={td}>{r.model}</td>
              <td style={td}>{r.dn ?? "—"}</td>
              <td style={td}>{r.d_over_dn ?? "—"}</td>
              <td style={td}>{r.max_n}</td>
              <td style={td}>{r.d_reg_pa}</td>
              <td style={td}>{r.eta_req}</td>
              <td style={td}>{r.n_shaft_kw}</td>
              <td style={td}>{r.motor ? `${r.motor.name} (${r.motor.n_kw} кВт)` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const th: CSSProperties = { padding: "6px 8px", color: "#444" };
const td: CSSProperties = { padding: "6px 8px" };
