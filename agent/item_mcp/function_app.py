"""Azure Functions entry point for item-mcp: wraps the FastMCP server in
mcp_server.py (itself wrapping the Item API) with azure-functions' ASGI
adapter, exposed as a single HTTP-triggered Azure Function.

host.json sets routePrefix to "" so this is exposed at exactly /mcp (the
same path FastMCP uses locally), not under the default /api prefix.
Provisioned by tofu/agent.tf (azurerm_function_app_flex_consumption.item_mcp).

host_origin_protection is disabled: it defends against DNS-rebinding
attacks on localhost-bound dev servers, which doesn't apply to a
cloud-hosted endpoint called server-to-server by the agent Function App.

NOTE: item state lives in this process's memory (see store.py) and, per
mcp_server.py's own docstring, "must stay one long-lived process shared
across tool calls" for item-creation/listing to behave consistently. A
Flex Consumption Function App can scale across multiple instances or
scale to zero between requests, so that guarantee no longer holds here --
items may appear to vanish or be inconsistent across calls. Fine for
exercising the deployment; not a substitute for real persistent storage.

Run locally with the Azure Functions Core Tools:
    func start
"""

import azure.functions as func

from mcp_server import mcp

asgi_app = mcp.http_app(host_origin_protection=False)
app = func.AsgiFunctionApp(app=asgi_app, http_auth_level=func.AuthLevel.ANONYMOUS)
