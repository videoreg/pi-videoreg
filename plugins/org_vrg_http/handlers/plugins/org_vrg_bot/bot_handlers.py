"""Telegram bot configuration handlers"""

from aiohttp import web


async def handle_bot_get_config(request: web.Request):
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("bot.get_settings", {})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_get_telegram_config: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_bot_config(request: web.Request):
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    data = await request.json()
  except Exception:
    return web.json_response({"error": "Invalid JSON"}, status=400)

  try:
    response = await api_client.exec("bot.set_settings", data)
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_set_telegram_config: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)
