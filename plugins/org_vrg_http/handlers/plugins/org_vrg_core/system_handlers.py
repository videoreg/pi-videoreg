"""HTTP handlers for the System page (services and plugins)"""

from aiohttp import web

from sdk.socket.requests import RequestTimeoutError


async def handle_get_system_info(request: web.Request):
  """List of services with status and plugins"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("core.get_system", {})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_get_system_info: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_set_plugin_enabled(request: web.Request):
  """Set the enabled flag for a plugin in the manifest"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    body = await request.json()
    plugin_id = body.get("id")
    enabled = body.get("enabled")

    if plugin_id is None or enabled is None:
      return web.json_response({"error": "Missing fields: id, enabled"}, status=400)

    response = await api_client.exec(
      "core.set_plugin_enabled", {"id": plugin_id, "enabled": enabled}
    )
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_set_plugin_enabled: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_service_action(request: web.Request):
  """Perform a service action: start, stop, restart"""
  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    body = await request.json()
    service = body.get("service")
    action = body.get("action")

    if not service or not action:
      return web.json_response({"error": "Missing fields: service, action"}, status=400)

    response = await api_client.exec("core.service_action", {"service": service, "action": action})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_service_action: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)
