import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import type { FanResult, SelectionQuery } from "./types";

// MCP-сервер fan-selector (streamable-http). Адрес можно переопределить через
// VITE_MCP_URL (например, .env: VITE_MCP_URL=http://host:port/mcp).
const MCP_URL: string =
  (import.meta.env.VITE_MCP_URL as string | undefined) ?? "http://127.0.0.1:8000/mcp";

let clientPromise: Promise<Client> | null = null;

function createClient(): Promise<Client> {
  return (async () => {
    const transport = new StreamableHTTPClientTransport(new URL(MCP_URL));
    const client = new Client({ name: "fan-selector-web", version: "0.1.0" });
    await client.connect(transport);
    return client;
  })();
}

async function getClient(): Promise<Client> {
  if (!clientPromise) {
    // При ошибке кэш сбрасывается, чтобы следующий вызов переподключился
    // (сервер мог быть ещё не запущен в момент первого запроса).
    clientPromise = createClient().catch((err) => {
      clientPromise = null;
      throw err;
    });
  }
  return clientPromise;
}

interface ToolContentBlock {
  type: string;
  text?: string;
}

function parseToolResult(result: unknown): FanResult {
  const content = (result as { content?: ToolContentBlock[] }).content ?? [];
  for (const block of content) {
    if (block.type === "text" && block.text) {
      return JSON.parse(block.text) as FanResult;
    }
  }
  throw new Error("Инструмент вернул пустой результат");
}

export async function selectFan(query: SelectionQuery): Promise<FanResult> {
  const client = await getClient();
  const result = await client.callTool({
    name: "select_fan",
    arguments: {
      q_req: query.q_req,
      p_req: query.p_req,
      pressure_type: query.pressure_type ?? "FULL",
      ...(query.d_reg_max !== undefined ? { d_reg_max: query.d_reg_max } : {}),
      ...(query.series?.length ? { series: query.series } : {}),
      ...(query.sizes?.length ? { sizes: query.sizes } : {}),
      ...(query.rpms?.length ? { rpms: query.rpms } : {}),
    },
  });
  if ((result as { isError?: boolean }).isError) {
    throw new Error("Ошибка подбора на стороне MCP-сервера");
  }
  return parseToolResult(result);
}

export async function lookupCatalog(
  series?: string[],
  dn?: number,
  d_over_dn?: number
): Promise<{ schema: string; count: number; items: unknown[] }> {
  const client = await getClient();
  const result = await client.callTool({
    name: "lookup_catalog",
    arguments: {
      ...(series?.length ? { series } : {}),
      ...(dn !== undefined ? { dn } : {}),
      ...(d_over_dn !== undefined ? { d_over_dn } : {}),
    },
  });
  return parseToolResult(result) as unknown as {
    schema: string;
    count: number;
    items: unknown[];
  };
}
