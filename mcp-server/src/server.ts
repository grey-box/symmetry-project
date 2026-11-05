import http from "node:http";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  type Tool,
} from "@modelcontextprotocol/sdk/types.js";

const API_BASE_URL = (process.env.SYMMETRY_API_URL ?? "http://127.0.0.1:8000")
  .replace(/\/$/, "");

async function callSymmetryApi(path: string, args: unknown): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(args),
      signal: AbortSignal.timeout(120_000),
    });
  } catch (error) {
    throw new Error(
      `Could not reach Symmetry API at ${API_BASE_URL}: ${error instanceof Error ? error.message : String(error)}`,
    );
  }

  const responseText = await response.text();
  let result: unknown;
  try {
    result = responseText ? JSON.parse(responseText) : {};
  } catch {
    result = responseText;
  }
  if (!response.ok) {
    throw new Error(`Symmetry API returned HTTP ${response.status}: ${typeof result === "string" ? result : JSON.stringify(result)}`);
  }
  return result;
}

const SEMANTIC_COMPARISON_TOOL: Tool = {
  name: "compare_articles",
  description:
    "Semantically compare two article texts and return sentences missing from the target and extra in the target.",
  inputSchema: {
    type: "object",
    properties: {
      original_article_content: { type: "string", minLength: 1 },
      translated_article_content: { type: "string", minLength: 1 },
      original_language: { type: "string", default: "en" },
      translated_language: { type: "string", default: "fr" },
      similarity_threshold: {
        type: "number",
        minimum: 0,
        maximum: 1,
        default: 0.75,
      },
      model_name: { type: "string", default: "sentence-transformers/LaBSE" },
    },
    required: ["original_article_content", "translated_article_content"],
    additionalProperties: false,
  },
};

function createServer() {
  const server = new Server(
    {
      name: "symmetry-mcp-server",
      version: "1.0.0",
    },
    {
      capabilities: {
        tools: {},
      },
    },
  );

  const HEALTH_TOOL: Tool = {
    name: "health_check",
    description:
      "Check whether the MCP server is alive and responding over streamable HTTP.",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false,
    },
  };

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: [HEALTH_TOOL, SEMANTIC_COMPARISON_TOOL],
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    if (name === "compare_articles") {
      try {
        const result = await callSymmetryApi(
          "/symmetry/v1/articles/compare",
          args ?? {},
        );
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      } catch (error) {
        return {
          isError: true,
          content: [
            {
              type: "text",
              text: error instanceof Error ? error.message : String(error),
            },
          ],
        };
      }
    }

    if (name !== "health_check") {
      throw new Error(`Unknown tool: ${name}`);
    }

    const payload = {
      ok: true,
      service: "symmetry-mcp-server",
      status: "healthy",
      endpoint: "/mcp",
      transport: "streamable-http",
      timestamp: new Date().toISOString(),
      args,
    };

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(payload, null, 2),
        },
      ],
    };
  });

  return server;
}

async function readJsonBody(req: http.IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];

  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }

  const raw = Buffer.concat(chunks).toString("utf8").trim();
  if (!raw) {
    return undefined;
  }

  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(
      `Invalid JSON in MCP request: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
}

async function handleMcpRequest(
  req: http.IncomingMessage,
  res: http.ServerResponse,
): Promise<void> {
  const method = req.method ?? "GET";
  const pathname = req.url
    ? new URL(req.url, `http://${req.headers.host ?? "localhost"}`).pathname
    : "/";

  if (pathname !== "/mcp") {
    res.writeHead(404, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "Not found" }));
    return;
  }

  if (method === "GET" || method === "DELETE") {
    res.writeHead(405, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        jsonrpc: "2.0",
        error: {
          code: -32000,
          message: "Method not allowed.",
        },
        id: null,
      }),
    );
    return;
  }

  if (method !== "POST") {
    res.writeHead(405, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "Method not allowed" }));
    return;
  }

  let parsedBody: unknown;
  try {
    parsedBody = await readJsonBody(req);
  } catch (error) {
    res.writeHead(400, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        jsonrpc: "2.0",
        error: {
          code: -32600,
          message:
            error instanceof Error ? error.message : "Invalid request body",
        },
        id: null,
      }),
    );
    return;
  }

  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
  });
  const mcpServer = createServer();

  await mcpServer.connect(transport);
  await transport.handleRequest(req, res, parsedBody as never);

  res.on("close", async () => {
    await transport.close();
    await mcpServer.close();
  });
}

async function main() {
  const host = process.env.HOST ?? "127.0.0.1";
  const port = Number(process.env.PORT ?? 3000);

  const server = http.createServer((req, res) => {
    void handleMcpRequest(req, res);
  });

  server.listen(port, host, () => {
    console.log(`Symmetry MCP server listening on http://${host}:${port}/mcp`);
  });
}

main().catch((error) => {
  console.error("Fatal server error:", error);
  process.exit(1);
});
