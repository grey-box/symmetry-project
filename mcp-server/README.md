# Symmetry MCP Server

This project runs a minimal Model Context Protocol (MCP) server over Streamable HTTP.

## Endpoint

- `POST /mcp`: MCP JSON-RPC request stream
- `GET /mcp`: unsupported for this server and returns 405
- `DELETE /mcp`: unsupported for this server and returns 405

## Tools

- `health_check`: Returns a JSON payload indicating the server is alive and healthy.

## Quick start

```bash
cd mcp-server
npm install
npm run build
npm start
```

The server listens on `http://127.0.0.1:3000/mcp` by default and is ready to be consumed by an MCP client using the Streamable HTTP transport.
