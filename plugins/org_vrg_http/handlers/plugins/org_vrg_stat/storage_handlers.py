"""Storage info handler"""

from aiohttp import web


async def handle_get_stat_storage_info(request: web.Request):
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("stat.storage_info", {})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_get_storage_info: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)
