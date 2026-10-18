"""Exposes the customers database as an MCP server: read_query/write_query
tools running raw SQL against customers.db via sqlite3.

customers.db isn't committed to the repo (see .gitignore) and a Flex
Consumption instance starts from a fresh filesystem on every cold start,
so the first call that touches it seeds it with dummy data.

Run with stdio transport (for Claude Desktop / Claude Code), from agent/
so customers_mcp resolves as a package:
    cd agent && uv run python -m customers_mcp.mcp_server

Run with HTTP transport:
    cd agent && uv run python -m customers_mcp.mcp_server --http

In production this is instead imported directly by agent/function_app.py,
which hosts it alongside chat and item-mcp on the same Function App.
"""

import json
import sys

from fastmcp import FastMCP

from customers_mcp.database import DB_PATH, get_connection
from customers_mcp.seed import seed as seed_customers

mcp: FastMCP = FastMCP("Customers API")


def _ensure_db() -> None:
    """A no-op once customers.db already exists (local dev, or a later
    call within the same warm instance)."""
    if not DB_PATH.exists():
        seed_customers()


@mcp.tool
def read_query(sql: str) -> str:
    """Run a read-only SQL SELECT query against the customers database and return the matching rows as JSON."""
    _ensure_db()
    with get_connection() as conn:
        rows = conn.execute(sql).fetchall()
        return json.dumps([dict(row) for row in rows])


@mcp.tool
def write_query(sql: str) -> str:
    """Run an INSERT/UPDATE/DELETE SQL statement against the customers database and return how many rows were affected."""
    _ensure_db()
    with get_connection() as conn:
        cursor = conn.execute(sql)
        conn.commit()
        return f"{cursor.rowcount} row(s) affected."


if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.run(transport="http", host="127.0.0.1", port=8011)
    else:
        mcp.run()
