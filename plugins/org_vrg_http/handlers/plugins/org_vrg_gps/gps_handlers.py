"""HTTP handlers for GPS tracks"""

from aiohttp import web

from sdk.socket.requests import RequestTimeoutError


async def handle_get_gps_tracks(request: web.Request):
  """List all GPS tracks"""
  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("gps.get_tracks", {})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_get_gps_tracks: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_delete_gps_track(request: web.Request):
  """Delete a GPS track by filename"""
  logger = request.app["logger"]
  api_client = request.app["api_client"]

  filename = request.match_info.get("filename", "")
  if not filename or "/" in filename or "\\" in filename or ".." in filename:
    return web.json_response({"error": "Invalid filename"}, status=400)

  try:
    response = await api_client.exec("gps.delete_track", {"filename": filename})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response({"status": "ok"})
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_delete_gps_track: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)
