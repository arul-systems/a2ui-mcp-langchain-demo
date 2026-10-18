"""HTTP backend for agent-ui/: wraps the LangChain agent in agent.py behind
a single POST /chat endpoint.

Each response is split into its plain-text portion and any validated A2UI
messages (using the same A2uiRequestProcessor the agent's system prompt is
built from -- see agent.A2UI_PROCESSOR / a2ui_support.build_processor) so
the React app can show the text in the chat log and feed the A2UI messages
to its A2UI renderer separately.

Requires item-mcp running over HTTP first (see agent/README.md):
    uv run python agent/item_mcp/mcp_server.py --http

Run this server:
    uv run uvicorn agent.server:app --reload --port 8000 --app-dir .
or, since this file lives in agent/ and uses plain (non-package) imports
like the rest of this directory:
    uv run uvicorn server:app --reload --port 8000 --app-dir agent
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2ui.parser import A2uiPart, TextPart
from agent import A2UI_PROCESSOR, run_agent
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Agent Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    text: str
    a2ui: list[dict]


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Runs one turn of the agent and splits its answer into text + A2UI."""
    content = await run_agent(request.message)

    try:
        parts = A2UI_PROCESSOR.parse_response(content)
    except Exception:
        # A malformed A2UI block: show the raw text rather than dropping the
        # turn, so the user still sees what the agent said.
        return ChatResponse(text=content, a2ui=[])

    text = "".join(part.text for part in parts if isinstance(part, TextPart)).strip()
    a2ui_messages = [
        message.model_dump(by_alias=True, exclude_none=True)
        for part in parts
        if isinstance(part, A2uiPart)
        for message in part.a2ui
    ]
    return ChatResponse(text=text, a2ui=a2ui_messages)
