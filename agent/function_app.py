"""Azure Functions entry point for the agent backend: a single native HTTP
trigger (no FastAPI/ASGI layer) that Azure invokes directly for POST /chat.

host.json sets routePrefix to "" so this is exposed at exactly /chat, not
under the default /api prefix. Provisioned by tofu/agent.tf
(azurerm_linux_function_app).

Each response is split into its plain-text portion and any validated A2UI
messages (using the same A2uiRequestProcessor the agent's system prompt is
built from -- see agent.A2UI_PROCESSOR / a2ui_support.build_processor) so
the React app can show the text in the chat log and feed the A2UI messages
to its A2UI renderer separately.

Run locally with the Azure Functions Core Tools:
    func start
"""

import json

import azure.functions as func

from a2ui.parser import A2uiPart, TextPart
from agent import A2UI_PROCESSOR, run_agent

app = func.FunctionApp()


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
