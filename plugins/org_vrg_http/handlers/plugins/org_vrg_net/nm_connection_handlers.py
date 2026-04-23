import json
from logging import Logger

from aiohttp import web

from sdk.socket.api import ApiClient, ApiResponse


async def handle_net_get_connection_config(request: web.Request):
  logger: Logger = request.app["logger"]
  api_client: ApiClient = request.app["api_client"]

  try:
    response: ApiResponse = await api_client.exec("net.connections", None)

    if not response.is_ok():
      return web.Response(
        status=500,
        text=json.dumps({"error": f"Failed to update WiFi configuration: {response.get_error()}"}),
        content_type="application/json",
      )

    return web.Response(text=json.dumps(response.get_data()), content_type="application/json")

  except Exception as e:
    logger.error(f"Error getting WiFi config: {e}")
    return web.Response(
      status=500,
      text=f'{{"error": "Failed to get WiFi config: {str(e)}"}}',
      content_type="application/json",
    )


async def handle_net_post_connection_config(request: web.Request):
  logger: Logger = request.app["logger"]
  api_client: ApiClient = request.app["api_client"]

  try:
    data = await request.json()
  except json.JSONDecodeError:
    return web.Response(
      status=400, text='{"error": "Invalid JSON"}', content_type="application/json"
    )

  try:
    response: ApiResponse = await api_client.exec("net.connection_update", data)

    if not response.is_ok():
      return web.Response(
        status=500,
        text=json.dumps({"error": f"Failed to update WiFi configuration: {response.get_error()}"}),
        content_type="application/json",
      )

    return web.Response(
      text='{"message": "WiFi configuration successfully updated"}', content_type="application/json"
    )

  except Exception as e:
    logger.error(f"Error setting WiFi config: {e}")
    return web.Response(
      status=500,
      text=f'{{"error": "Failed to set WiFi config: {str(e)}"}}',
      content_type="application/json",
    )


async def handle_net_post_connection_enable(request: web.Request):
  logger: Logger = request.app["logger"]
  api_client: ApiClient = request.app["api_client"]

  try:
    data = await request.json()
  except json.JSONDecodeError:
    return web.Response(
      status=400, text='{"error": "Invalid JSON"}', content_type="application/json"
    )

  try:
    if data.get("enabled", False):
      method = "net.connection_up"
    else:
      method = "net.connection_down"

    response: ApiResponse = await api_client.exec(method, data.get("type"))

    if not response.is_ok():
      return web.Response(
        status=500,
        text=json.dumps({"error": f"Failed to update WiFi configuration: {response.get_error()}"}),
        content_type="application/json",
      )

    return web.Response(
      text='{"message": "WiFi configuration successfully updated"}', content_type="application/json"
    )

  except Exception as e:
    logger.error(f"Error setting WiFi config: {e}")
    return web.Response(
      status=500,
      text=f'{{"error": "Failed to set WiFi config: {str(e)}"}}',
      content_type="application/json",
    )


async def handle_net_set_wifi_block(request: web.Request):
  logger: Logger = request.app["logger"]
  api_client: ApiClient = request.app["api_client"]

  try:
    data = await request.json()
  except json.JSONDecodeError:
    return web.Response(
      status=400, text='{"error": "Invalid JSON"}', content_type="application/json"
    )

  try:
    if data.get("blocked", False):
      method = "net.wifi_block"
    else:
      method = "net.wifi_unblock"

    response: ApiResponse = await api_client.exec(method, None)

    if not response.is_ok():
      return web.Response(
        status=500,
        text=json.dumps({"error": f"Failed to update WiFi configuration: {response.get_error()}"}),
        content_type="application/json",
      )

    return web.Response(
      text='{"message": "WiFi configuration successfully updated"}', content_type="application/json"
    )

  except Exception as e:
    logger.error(f"handle_set_wifi_blocked error {type(e).__name__}: {e}")
    return web.Response(
      status=500,
      text=f'{{"error": "Failed to update WiFi configuration: {str(e)}"}}',
      content_type="application/json",
    )
