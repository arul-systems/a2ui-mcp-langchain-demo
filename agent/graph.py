"""Single-node LangGraph that uses an LLM agent to manage the item catalog
and look up customer data, via MCP tools.

Server definitions live in a single place, .mcp.json at the repo root,
instead of being duplicated here. This loads it and builds a
langchain-mcp-adapters MultiServerMCPClient with one connection per server
listed there:

- "item-mcp": streamable HTTP, pointing at an already-running server.
  Item state lives in that process's memory, so it must stay one
  long-lived process shared across calls; a fresh subprocess per call
  would lose previously added items. Start it first:
      uv run python agent/item-mcp/mcp_server.py --http
- "customers-mcp": stdio, spawned on demand. Safe to spawn fresh per tool
  call (langchain-mcp-adapters opens a new session -- a new subprocess,
  for stdio -- per call) because its state lives in the customers.db
  file on disk, not in the process.

Also requires OPENAI_API_KEY to be set (e.g. in a .env file at the repo root).

Every tool call the agent makes -- including the literal SQL text sent to
customers-mcp's read_query/write_query tools -- is printed as it happens,
followed by the final answer.

Run this graph:
    uv run python agent/graph.py
"""

import asyncio
import json
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
load_dotenv()

from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import END, START, StateGraph


MCP_CONFIG_PATH = Path(__file__).resolve().parent.parent / ".mcp.json"
MODEL = "openai:gpt-4.1"

SYSTEM_PROMPT = (
    "You manage an item catalog and look up customer records through the "
    "provided tools. Always use the tools to add/list/get items and to "
    "query customer data, and read back results; compute totals, counts, "
    "and other math yourself from the tool results rather than guessing."
)


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


class State(TypedDict):
    query: str
    result: str


def _print_tool_trace(messages: list[BaseMessage]) -> None:
    """Print every tool call the agent made and the result it got back, in order."""
    for message in messages:
        for call in getattr(message, "tool_calls", None) or []:
            print(f"[CALL]   {call['name']}({call['args']})")
        if isinstance(message, ToolMessage):
            print(f"[RESULT] {message.name}: {message.content}")


async def agent_node(state: State) -> State:
    client = MultiServerMCPClient(_load_mcp_connections(MCP_CONFIG_PATH))
    tools = await client.get_tools()
    agent = create_agent(MODEL, tools, system_prompt=SYSTEM_PROMPT)
    response = await agent.ainvoke({"messages": [{"role": "user", "content": state["query"]}]})
    _print_tool_trace(response["messages"])
    return {"result": response["messages"][-1].content}


graph_builder = StateGraph(State)
graph_builder.add_node("agent_node", agent_node)
graph_builder.add_edge(START, "agent_node")
graph_builder.add_edge("agent_node", END)
graph = graph_builder.compile()


async def main() -> None:
    query = (
        "Add a new item called 'Widget' priced at $9.99 with 10 in stock, "
        "then list all items in the catalog. Separately, tell me how many "
        "customers are from India."
    )
    result = await graph.ainvoke({"query": query, "result": ""})
    print(result["result"])


if __name__ == "__main__":
    asyncio.run(main())
