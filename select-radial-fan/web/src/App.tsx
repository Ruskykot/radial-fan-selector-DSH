import { useState } from "react";
import type { FanResult, SelectionQuery } from "./types";
import { selectFan } from "./api";
import FanForm from "./components/FanForm";
import ResultTable from "./components/ResultTable";
import FanChart from "./components/FanChart";

export default function App() {
  const [result, setResult] = useState<FanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(query: SelectionQuery) {
    setLoading(true);
    setError(null);
    try {
      setResult(await selectFan(query));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 1240, margin: "0 auto", padding: 16 }}>
      <h1 style={{ margin: "0 0 4px" }}>Подбор радиального вентилятора</h1>
      <p style={{ margin: "0 0 16px", color: "#555" }}>
        Серии ВР 86-77 и ВР 280-46 — по расходу и давлению
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 16, alignItems: "start" }}>
        <FanForm onSubmit={handleSubmit} loading={loading} />
        <div style={{ minWidth: 0 }}>
          {error && (
            <div style={{ color: "#b00020", marginBottom: 12 }}>
              Ошибка: {error} — запустите MCP-сервер (python mcp_stdio.py streamable-http) или задайте VITE_MCP_URL.
            </div>
          )}
          {result && result.error && (
            <div style={{ color: "#b00020", marginBottom: 12 }}>{result.error.message}</div>
          )}
          {result && !result.error && (
            <>
              <ResultTable result={result} />
              <FanChart result={result} />
            </>
          )}
        </div>
      </div>
    </main>
  );
}
