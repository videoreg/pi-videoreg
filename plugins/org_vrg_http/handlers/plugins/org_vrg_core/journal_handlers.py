"""HTTP handlers for the journal"""

from aiohttp import web

from sdk.socket.requests import RequestTimeoutError


async def handle_get_journal(request: web.Request):
  """Get combined journal content for the last 2 days"""
  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("core.get_journal_files", {})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)

    files = response.get_data().get("files", [])
    lines = []
    for file_path in files:
      try:
        with open(file_path, encoding="utf-8") as f:
          for line in f:
            line = line.strip()
            if line:
              lines.append(line)
      except FileNotFoundError:
        pass

    return web.json_response({"lines": lines})
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_get_journal: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)
