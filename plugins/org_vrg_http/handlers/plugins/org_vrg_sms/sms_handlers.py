"""HTTP handlers for SMS inbox"""

import os

from aiohttp import web

from sdk.socket.requests import RequestTimeoutError


async def handle_get_sms(request: web.Request):
  """List all SMS messages"""
  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("sms.get_all_sms", {})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_get_sms_inbox: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_delete_sms(request: web.Request):
  """Delete an SMS message by filename"""
  logger = request.app["logger"]
  videoreg = request.app["videoreg"]

  filename = request.match_info.get("filename", "")
  if not filename or "/" in filename or "\\" in filename or ".." in filename:
    return web.json_response({"error": "Invalid filename"}, status=400)

  try:
    file_path = videoreg.sms_path(f"{filename}.json")
    if not file_path.exists():
      return web.json_response({"error": "Not found"}, status=404)
    os.remove(file_path)
    return web.json_response({"status": "ok"})
  except Exception as e:
    logger.error(f"Error in handle_delete_sms: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)
