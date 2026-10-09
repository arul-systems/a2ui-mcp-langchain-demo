# Item API

A simple REST API for managing an item catalog: add, list, and get items.
Catalog state is held **in memory** for the lifetime of the server process —
nothing is persisted to disk, and state is lost on restart.

## Running

```bash
uv run uvicorn main:app --reload --app-dir agent/item-mcp
```

- Interactive docs: http://127.0.0.1:8000/docs
- Raw OpenAPI schema: http://127.0.0.1:8000/openapi.json

## Concepts

- **Item**: gets a unique, server-generated `id` (UUID string). Has `name`,
  `description` (optional), `price` (≥ 0), and `quantity` (≥ 0).

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| POST | `/items` | Add a new item. Body: `{name, description?, price, quantity?}`. |
| GET | `/items` | List all items in the catalog. |
| GET | `/items/{item_id}` | Get a single item. 404 if not found. |

### Example flow

```bash
curl -X POST localhost:8000/items \
  -H 'Content-Type: application/json' \
  -d '{"name": "Widget", "price": 9.99, "quantity": 10}'
# -> {"id": "<item_id>", "name": "Widget", "description": null, "price": 9.99, "quantity": 10}

curl localhost:8000/items
curl localhost:8000/items/<item_id>
```

## Using this with MCP

Every route has a `summary`, a docstring (exposed as `description`), and a
`tags` grouping (`items`) baked into its OpenAPI operation, and every
request/response field carries a `description` via Pydantic `Field(...)`.
This is exactly the metadata [`FastMCP`](https://github.com/jlowin/fastmcp)
uses to name tools and write the descriptions/input-schema an LLM sees.

`mcp_server.py` turns the FastAPI app directly into an MCP server, one tool
per route, via `FastMCP.from_fastapi`:

```python
from fastmcp import FastMCP
from main import app as fastapi_app

mcp = FastMCP.from_fastapi(app=fastapi_app, name="Item API")
```

`fastmcp` calls into the FastAPI app in-process (ASGI), so there's no need
to run `uvicorn` separately — the MCP server *is* the API server.

**Run over HTTP** (used by the LangChain agent in `agent/graph.py`, since
item state lives in server memory and must stay one long-lived process
shared across tool calls):

```bash
uv run python agent/item-mcp/mcp_server.py --http
# serves MCP at http://127.0.0.1:8010/mcp
```

**Run over stdio** (for Claude Desktop / Claude Code as a local MCP server):

```bash
uv run python agent/item-mcp/mcp_server.py
```
