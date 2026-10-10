# Symmetry MCP Server

This project scaffolds a minimal Model Context Protocol (MCP) server that speaks over stdio.

## Tools

- `health_check`: Returns a JSON payload indicating the server is alive and healthy.

## Quick start

```bash
cd mcp-server
npm install
npm run build
npm start
```

The server listens on standard input/output and is ready to be consumed by an MCP client.
