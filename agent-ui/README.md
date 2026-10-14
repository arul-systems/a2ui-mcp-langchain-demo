# agent-ui

A small React (Vite + TypeScript) chat app for the LangGraph agent in
`agent/`. It has one chat window: type a question, the agent's answer is
printed. When the agent responds with an A2UI JSON block (e.g. the
item-creation form from `../agent/a2ui`), it's rendered
using the official **A2UI renderer** (`@a2ui/react` + `@a2ui/web_core`)
instead of being shown as raw JSON.

## How it talks to the agent

There's no direct connection to the LangGraph agent or MCP servers — this
app only calls one HTTP endpoint, `POST /chat`, on `agent/server.py` (a
small FastAPI wrapper around `agent/graph.py`). That endpoint returns:

```json
{ "text": "...", "a2ui": [ /* validated A2UI v0.9 messages, if any */ ] }
```

`text` is appended to the chat log. `a2ui`, if non-empty, is fed into a
`MessageProcessor` (`@a2ui/web_core/v0_9`), which is what `A2uiSurface`
(`@a2ui/react/v0_9`) renders from.

### Form submission

The rendered form's submit button carries an A2UI `action` (`name:
"create_item"`, with the entered field values in its `context`). The
`MessageProcessor`'s action handler turns that into a plain-language chat
message ("Create an item named ... with description ..., price ...,
quantity ...") and sends it back through the same `/chat` endpoint, as if
the user had typed it — the agent then calls item-mcp's `add_item` tool
with those values, same as any other turn.

## Running

This needs three processes running, from the repo root:

```bash
# 1. Item API over HTTP (item state lives in this process)
uv run python agent/item_mcp/mcp_server.py --http

# 2. Chat backend (needs OPENAI_API_KEY in .env, see ../agent/README.md)
uv run uvicorn server:app --app-dir agent --port 8000

# 3. This app
cd agent-ui
npm install   # first time only
npm run dev   # http://localhost:5173
```

`customers-mcp` doesn't need its own process — it's spawned on demand over
stdio by the agent, same as in the CLI (`agent/graph.py`) flow.

## Scripts

- `npm run dev` — Vite dev server.
- `npm run build` — type-checks (`tsc -b`) and builds to `dist/`.
- `npm run preview` — serves the production build locally.
