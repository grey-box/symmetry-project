import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  type Tool,
} from "@modelcontextprotocol/sdk/types.js";

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
  description: "Check whether the MCP server is alive and responding over stdio.",
  inputSchema: {
    type: "object",
    properties: {},
    additionalProperties: false,
  },
};

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [HEALTH_TOOL],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name !== "health_check") {
    throw new Error(`Unknown tool: ${name}`);
  }

  const payload = {
    ok: true,
    service: "symmetry-mcp-server",
    status: "healthy",
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

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Symmetry MCP server running on stdio");
}

main().catch((error) => {
  console.error("Fatal server error:", error);
  process.exit(1);
});
