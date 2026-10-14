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

Run this graph:
    uv run python agent/graph.py
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2ui.parser import A2uiPart
from a2ui_support import build_processor
from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import END, START, StateGraph


REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_CONFIG_PATH = REPO_ROOT / ".mcp.json"
MODEL = "openai:gpt-4.1"

A2UI_PROCESSOR = build_processor()

SYSTEM_PROMPT = (
    "You manage an item catalog and look up customer records through the "
    "provided tools. Always use the tools to add/list/get items and to "
    "query customer data, and read back results; compute totals, counts, "
    "and other math yourself from the tool results rather than guessing.\n\n"
    "When the user wants to create/add a new item but hasn't given you "
    "concrete values for all of its fields in their message, don't guess "
    "values or ask for them one-by-one in chat -- instead, respond with an "
    'A2UI JSON block for a surface named "item_creation", following the '
    "schema and example below.\n\n"
    "When the user wants to see item/catalog details (list items, view the "
    "catalog, etc.), call the list-items tool first, then respond with an "
    'A2UI JSON block for a surface named "item_table" instead of describing '
    "the items in plain text, following the schema and example below. "
    "Populate its /items data-model path with the real items from the "
    "tool's result (each as {name, description, price, quantity}), not the "
    "example's placeholder rows.\n\n"
    f"{A2UI_PROCESSOR.prompt_snippet}"
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
    final_text = response["messages"][-1].content
    # _print_a2ui_parts(final_text)
    return {"result": final_text}


graph_builder = StateGraph(State)
graph_builder.add_node("agent_node", agent_node)
graph_builder.add_edge(START, "agent_node")
graph_builder.add_edge("agent_node", END)
graph = graph_builder.compile()


async def main() -> None:
    query = (
        "Create new item"
    )
    result = await graph.ainvoke({"query": query, "result": ""})
    print(result["result"])

    print("\n---\n")

    a2ui_query = "I'd like to create a new item for the catalog."
    a2ui_result = await graph.ainvoke({"query": a2ui_query, "result": ""})
    print(a2ui_result["result"])


if __name__ == "__main__":
    asyncio.run(main())
