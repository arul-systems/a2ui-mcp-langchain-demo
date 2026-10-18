"""LangChain agent that manages an item catalog and looks up customer data,
via MCP tools.

Server definitions live in a single place, .mcp.json: checked in at the
repo root for local dev, but copied alongside this file by the deploy
workflow since it needs to ship inside the Azure Functions package (see
_find_mcp_config). This loads it and builds a langchain-mcp-adapters
MultiServerMCPClient with one connection per server listed there:

- "item-mcp": item_mcp/mcp_server.py's FastMCP server. Item state lives in
  that process's memory, so it must stay one long-lived process shared
  across calls -- a fresh instance per call would lose previously added
  items. Locally, an already-running server reachable over streamable
  HTTP (uv run python agent/item_mcp/mcp_server.py --http); deployed,
  it's the /mcp function co-hosted on this same Function App
  (agent/function_app.py, tofu/agent.tf).
- "customers-mcp": customers_mcp/mcp_server.py's FastMCP server
  (read_query/write_query against customers.db). No long-lived-process
  requirement, since its state lives on disk, not in memory. Deployed,
  it's the /customers-mcp function on this same Function App.

Also requires OPENAI_API_KEY to be set (e.g. in a .env file at the repo root).

The agent is also A2UI-enabled (see ../a2ui/ and a2ui_support.py) -- not as
a tool, but as the agent's own LLM output: its system prompt is extended
with an A2uiRequestProcessor's prompt_snippet (a2ui.processor), which
carries the A2UI v0.9 JSON schema plus a validated few-shot example of the
item-creation surface declared in a2ui/forms/item_creation.json. When a
user wants to create an item without having already given concrete field
values, the agent responds with an A2UI JSON block directly (wrapped in
<a2ui-json> tags) instead of plain text; the response is then run through
processor.parse_response, which validates it against the same schema.

Every tool call the agent makes -- including the literal SQL text sent to
customers-mcp's read_query/write_query tools -- is printed as it happens,
followed by any validated A2UI messages found in the final answer.

Run this agent:
    uv run python agent/agent.py
"""

import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from a2ui.parser import A2uiPart
from a2ui_support import build_processor
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

A2UI_PROCESSOR = build_processor()

SYSTEM_PROMPT = (
    f""" You manage an item catalog and look up customer records through the
provided tools. Always use the tools to add/list/get items and to
query customer data, and read back results; compute totals, counts,
and other math yourself from the tool results rather than guessing.\n\n
When the user wants to create/add a new item but hasn't given you
concrete values for all of its fields in their message, don't guess. \n\n

After successful creation of customer/item ask user what else they need todo next.

{A2UI_PROCESSOR.prompt_snippet}"""
)


def _print_a2ui_parts(content: str) -> None:
    """Parses the agent's final response for an embedded A2UI JSON block,
    validating it against the catalog schema via the A2UI processor, and
    prints the validated messages. A plain-text answer has no A2UI block,
    which parses to an empty result, not an error.
    """
    try:
        parts = A2UI_PROCESSOR.parse_response(content)
    except Exception as e:
        print(f"[A2UI] response included an invalid A2UI block: {e}")
        return
    for part in parts:
        if isinstance(part, A2uiPart):
            for message in part.a2ui:
                print(f"[A2UI] {message.model_dump_json(by_alias=True, exclude_none=True)}")


def _load_mcp_connections(config_path: Path) -> dict[str, dict]:
    """Build langchain-mcp-adapters connection configs from an .mcp.json file.

    .mcp.json entries omit the explicit "transport" key that
    langchain-mcp-adapters requires; it's inferred here instead (stdio for
    command-based entries, streamable_http for url-based ones).
    """
    servers = json.loads(config_path.read_text())["mcpServers"]
    connections: dict[str, dict] = {}
    for name, server in servers.items():
        if "url" in server:
            connections[name] = {"transport": "streamable_http", "url": server["url"]}
        else:
            connections[name] = {
                "transport": "stdio",
                "command": server["command"],
                "args": server.get("args", []),
                "cwd": server.get("cwd"),
            }
    return connections


def _find_mcp_config() -> Path:
    """Locates .mcp.json: checked in at the repo root for local dev, one
    directory above this file. The deploy workflow copies it to sit
    alongside agent.py instead, since the Azure Functions package is this
    directory's contents flattened to the site root -- there's no
    separate parent directory once deployed.
    """
    here = Path(__file__).resolve().parent
    for candidate in (here / ".mcp.json", here.parent / ".mcp.json"):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No .mcp.json found next to {here} or its parent")


async def run_agent(query: str) -> str:
    """Runs one turn of the LangChain agent for the given user query and
    returns its final text response (which may embed an A2UI JSON block).
    """
    # Get all tool defs from the MCP servers
    client = MultiServerMCPClient(_load_mcp_connections(_find_mcp_config()))
    tools = await client.get_tools()

    # Invoke the agent with user message
    agent = create_agent("openai:gpt-4.1", tools, system_prompt=SYSTEM_PROMPT)
    response = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})

    # Return agent response
    return response["messages"][-1].content
