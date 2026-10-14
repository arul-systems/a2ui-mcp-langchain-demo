# Agent

A LangChain/LangGraph agent that acts as an MCP **client**, consuming two
local MCP servers:

- [`item_mcp`](item_mcp/) — a FastAPI "Item API" (add/list/get items),
  exposed as an MCP server via FastMCP.
- [`customers_mcp`](customers_mcp/) — a SQLite customers table, exposed
  as an MCP server via the official `mcp-server-sqlite` reference server.

Server connection details live in `.mcp.json` at the repo root; `graph.py`
reads that file to build its MCP connections rather than hardcoding them.

It's also A2UI-enabled (see `a2ui_support.py` and [`a2ui`](a2ui/)):
when a user wants to create an item without having given concrete field
values, the agent's own LLM output includes an A2UI JSON block for an
item-creation form, validated via `a2ui.processor`/`a2ui.parser`
(`a2ui-agent-sdk`) — there's no separate tool for this.

## One-time setup

```bash
uv sync
uv run python agent/customers_mcp/seed.py   # creates & seeds customers.db
```

Set `OPENAI_API_KEY` in a `.env` file at the repo root.

## Running the CLI demo

1. Start the item-mcp server over HTTP (item state lives in this process's
   memory, so it must stay running and shared across tool calls):

   ```bash
   uv run python agent/item_mcp/mcp_server.py --http
   ```

2. In another terminal, run the agent (customers-mcp is spawned on demand
   over stdio, so nothing else needs to be started for it):

   ```bash
   uv run python agent/graph.py
   ```

The agent prints every MCP tool call it makes (including the raw SQL sent
to `customers_mcp`), followed by its final answer.

## Running the chat UI

See [`../agent-ui/README.md`](../agent-ui/README.md) for the React chat
app. In short, on top of item-mcp (above), also run:

```bash
uv run uvicorn server:app --app-dir agent --port 8000   # agent/server.py
```

then `npm install && npm run dev` in `agent-ui/`.
