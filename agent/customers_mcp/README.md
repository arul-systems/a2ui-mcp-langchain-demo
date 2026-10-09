# Customers DB

A table of customer records, stored in a **SQLite** database
(``) and exposed over MCP using the official
[`mcp-server-sqlite`](https://pypi.org/project/mcp-server-sqlite/) reference
server — it runs arbitrary SQL against the database directly, so there's no
hand-written tool code to maintain and no query-writing on your end: the LLM
writes the SQL itself.

## Setup

Create the table and load ~50 dummy customers:

```bash
uv run python agent/customers-mcp/seed.py
```

This drops and recreates `customers` from `schema.sql`, then inserts the
dummy rows. Re-run any time to reset to a fresh, known dataset.

## Concepts

- **Customer**: a row in `customers`. Has a server-generated `id`, `name`,
  `email`, `phone`, `city`, `country`, and `created_at`.

## Architecture

- `schema.sql` — table definition.
- `database.py` — SQLite connection helper (`init_db`, `get_connection`), used by `seed.py`.
- `seed.py` — generates and inserts the dummy dataset.

MCP access goes through `mcp-server-sqlite` (installed as a project
dependency), pointed at ``:

| Tool | Description |
| --- | --- |
| `read_query` | Run a `SELECT` query. |
| `write_query` | Run an `INSERT`/`UPDATE`/`DELETE` query. |
| `create_table` | Run a `CREATE TABLE` statement. |
| `list_tables` | List all tables in the database. |
| `describe_table` | Get column info for a table. |
| `append_insight` | Append a note to an in-memory "business insights" memo. |

## Running the MCP server

**Seed the database first** (see Setup above).

This repo's `.mcp.json` already registers it for Claude Code / the LangChain
agent under the project root:

```json
{
  "mcpServers": {
    "customers-mcp": {
      "command": "uv",
      "args": ["run", "mcp-server-sqlite", "--db-path", "agent/customers-mcp/customers.db"],
      "cwd": "/Users/rshankar/ravi/projects/agentic_ai/a2ui-mcp-langchain-demo"
    }
  }
}
```

To run it standalone:

```bash
uv run mcp-server-sqlite --db-path agent/customers-mcp/customers.db
```
