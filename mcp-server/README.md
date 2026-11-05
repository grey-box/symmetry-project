# Symmetry MCP Server

This project runs a Model Context Protocol (MCP) server over Streamable HTTP and exposes Symmetry's article comparison capabilities to MCP clients.

## Endpoint

- `POST /mcp`: MCP JSON-RPC request stream
- `GET /mcp`: unsupported for this server and returns 405
- `DELETE /mcp`: unsupported for this server and returns 405

## Tools

- `health_check`: Returns a JSON payload indicating the MCP server is alive and healthy.
- `compare_articles`: Semantically compares two supplied article texts. Returns missing and extra sentences and comparison details.
- `compare_article_sections`: Fetches two Wikipedia articles by title or URL and returns section and paragraph level diffs.

Comparison tools call the Symmetry backend at `SYMMETRY_API_URL` (default `http://127.0.0.1:8000`). Start the backend before calling either comparison tool. The backend endpoints used are `/symmetry/v1/articles/compare` and `/symmetry/v1/articles/compare-sections`.

## Quick start

```bash
cd mcp-server
npm install
npm run build
npm start
```

The server listens on `http://127.0.0.1:3000/mcp` by default and is ready to be consumed by an MCP client using the Streamable HTTP transport. Set `SYMMETRY_API_URL` if the backend is hosted at a different URL; `HOST` and `PORT` configure the MCP listener.
