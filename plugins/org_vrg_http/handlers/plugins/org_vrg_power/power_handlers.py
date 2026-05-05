"""HTTP handlers for the Power page (PiSugar UPS)"""

from aiohttp import web


async def handle_get_power_status(request: web.Request):
  """Power status: battery, charging, temperature, uptime, wakeup"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("power.get_status", {})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_get_power_status: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_get_power_wakeup(request: web.Request):
  """Current wakeup mode and list of available options"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("power.get_wakeup_config", {})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_get_power_wakeup: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_set_power_wakeup(request: web.Request):
  """Set wakeup mode"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    body = await request.json()
    value = body.get("value")
    if not value:
      return web.json_response({"error": "Missing field: value"}, status=400)
    response = await api_client.exec("power.set_wakeup", value)
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_set_power_wakeup: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_get_power_charging_protection(request: web.Request):
  """Get battery charge protection setting (limit charge to 80%)"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("power.get_charging_protection", {})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_get_power_charging_protection: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_post_power_charging_protection(request: web.Request):
  """Toggle battery charge protection"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    body = await request.json()
    enabled = body.get("enabled")
    if not isinstance(enabled, bool):
      return web.json_response({"error": "Missing or invalid field: enabled"}, status=400)
    response = await api_client.exec("power.set_charging_protection", enabled)
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_post_power_charging_protection: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_post_power_reboot(request: web.Request):
  """System reboot"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("power.reboot", {"reason": "manual"})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_post_power_reboot: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_post_power_keep_alive(request: web.Request):
  """Keep the device on for the specified number of minutes"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    body = await request.json()
    minutes = int(body.get("minutes", 5))
    response = await api_client.exec("power.keep_alive", {"minutes": minutes})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_post_power_keep_alive: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_post_power_shutdown(request: web.Request):
  """System shutdown"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("power.shutdown", "manual")
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_post_power_shutdown: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)
