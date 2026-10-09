"""Exposes the Item API as an MCP server, generating one tool per route
from the FastAPI app's OpenAPI schema (summaries, docstrings, and field
descriptions all flow through automatically).

Run with stdio transport (for Claude Desktop / Claude Code):
    uv run python agent/item-mcp/mcp_server.py

Run with HTTP transport (for remote MCP clients, e.g. the LangChain agent
in agent/graph.py -- required because item state lives in this process's
memory and must stay one long-lived process shared across tool calls):
    uv run python agent/item-mcp/mcp_server.py --http
"""

# uv run python agent/item_mcp/mcp_server.py --http
import sys

from fastmcp import FastMCP

from main import app as fastapi_app

mcp: FastMCP = FastMCP.from_fastapi(app=fastapi_app, name="Item API")

if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.run(transport="http", host="127.0.0.1", port=8010)
    else:
        mcp.run()
