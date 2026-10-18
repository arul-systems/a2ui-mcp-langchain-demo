"""Azure Functions entry point for the agent backend. Hosts two functions
on the same Function App (tofu/agent.tf's
azurerm_function_app_flex_consumption.agent):

- chat: a native HTTP trigger (no FastAPI/ASGI layer) that Azure invokes
  directly for POST /chat.
- customers-mcp: the FastMCP server in customers_mcp/mcp_server.py
  (read_query/write_query against customers.db), exposed at
  /customers-mcp via azure-functions' ASGI adapter -- the same thing
  .mcp.json's "customers-mcp" entry talks to.

item-mcp is deployed separately (agent/item_mcp/function_app.py, its own
Function App in tofu/agent.tf) rather than co-hosted here.

host.json sets routePrefix to "" so these are exposed at exactly /chat
and /customers-mcp, not under the default /api prefix.

Each /chat response is split into its plain-text portion and any
validated A2UI messages (using the same A2uiRequestProcessor the agent's
system prompt is built from -- see agent.A2UI_PROCESSOR /
a2ui_support.build_processor) so the React app can show the text in the
chat log and feed the A2UI messages to its A2UI renderer separately.

Run locally with the Azure Functions Core Tools:
    func start
"""

import json

import azure.functions as func

from a2ui.parser import A2uiPart, TextPart
from agent import A2UI_PROCESSOR, run_agent
from customers_mcp.mcp_server import mcp as customers_mcp

app = func.FunctionApp()

# host_origin_protection defends against DNS-rebinding attacks on
# localhost-bound dev servers, which doesn't apply to a cloud-hosted
# endpoint called server-to-server by this same app's /chat.
_customers_mcp_asgi = func.AsgiMiddleware(customers_mcp.http_app(host_origin_protection=False))
_customers_mcp_started = False


@app.route(route="customers-mcp", methods=[m for m in func.HttpMethod], auth_level=func.AuthLevel.ANONYMOUS)
async def customers_mcp_route(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    global _customers_mcp_started
    if not _customers_mcp_started:
        if not await _customers_mcp_asgi.notify_startup():
            raise RuntimeError("customers-mcp ASGI app startup failed.")
        _customers_mcp_started = True
    return await _customers_mcp_asgi.handle_async(req, context)


@app.route(route="chat", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def chat(req: func.HttpRequest) -> func.HttpResponse:
    """Runs one turn of the agent and splits its answer into text + A2UI."""
    try:
        user_message = req.get_json()["message"]
        if not isinstance(user_message, str):
            raise ValueError
    except (ValueError, KeyError):
        return func.HttpResponse(
            json.dumps({"error": 'Request body must be JSON: {"message": <string>}'}),
            status_code=400,
            mimetype="application/json",
        )

    content = await run_agent(user_message)

    try:
        parts = A2UI_PROCESSOR.parse_response(content)
    except Exception:
        # A malformed A2UI block: show the raw text rather than dropping the
        # turn, so the user still sees what the agent said.
        return func.HttpResponse(
            json.dumps({"text": content, "a2ui": []}),
            mimetype="application/json",
        )

    text = "".join(part.text for part in parts if isinstance(part, TextPart)).strip()
    a2ui_messages = [
        message.model_dump(by_alias=True, exclude_none=True)
        for part in parts
        if isinstance(part, A2uiPart)
        for message in part.a2ui
    ]
    return func.HttpResponse(
        json.dumps({"text": text, "a2ui": a2ui_messages}),
        mimetype="application/json",
    )
