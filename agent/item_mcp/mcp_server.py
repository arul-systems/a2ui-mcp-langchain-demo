"""Exposes the Item API as an MCP server, generating one tool per route
from the FastAPI app's OpenAPI schema (summaries, docstrings, and field
descriptions all flow through automatically).

Run with stdio transport (for Claude Desktop / Claude Code):
    uv run python agent/item_mcp/mcp_server.py

Run with HTTP transport (for remote MCP clients, e.g. the LangChain agent
in agent/agent.py -- required because item state lives in this process's
memory and must stay one long-lived process shared across tool calls):
    uv run python agent/item_mcp/mcp_server.py --http

In production this is instead imported by agent/item_mcp/function_app.py,
item-mcp's own Function App (tofu/agent.tf) -- a separate deployment from
the main agent/customers-mcp Function App, since item state here lives
in this process's memory and item-mcp's deploy package is this
directory's contents flattened to its own site root, with no agent/
parent in that context -- hence the flat imports below rather than
item_mcp.-qualified ones.
"""

import sys

from fastmcp import FastMCP

from main import app as fastapi_app

mcp: FastMCP = FastMCP.from_fastapi(app=fastapi_app, name="Item API")

if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.run(transport="http", host="127.0.0.1", port=8010)
    else:
        mcp.run()
