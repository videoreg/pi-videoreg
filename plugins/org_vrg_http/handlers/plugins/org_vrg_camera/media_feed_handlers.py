"""HTTP handler for the media feed"""

from aiohttp import web


async def handle_get_camera_list(request: web.Request):
  """Combined list of videos and photos (all items, no pagination)"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("camera.list_media", {"all": True})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_get_media_feed: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_get_camera_convert_check(request: web.Request):
  """Check MP4 readiness for a specific video"""
  from sdk.socket.requests import RequestTimeoutError

  name = request.rel_url.query.get("name", "").strip()
  if not name:
    return web.json_response({"error": "name required"}, status=400)

  try:
    response = await request.app["api_client"].exec("camera.check_video_ready", {"name": name})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    request.app["logger"].error(f"Error in handle_get_check_video: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_post_camera_convert(request: web.Request):
  """Start H.264 → MP4 conversion in background"""
  from sdk.socket.requests import RequestTimeoutError

  try:
    body = await request.json()
    name = body.get("name", "").strip()
  except Exception:
    return web.json_response({"error": "invalid body"}, status=400)

  if not name:
    return web.json_response({"error": "name required"}, status=400)

  try:
    response = await request.app["api_client"].exec("camera.convert_video", {"name": name})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    request.app["logger"].error(f"Error in handle_post_convert_video: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_get_camera_fave_list(request: web.Request):
  """List of media files from the favorites folder"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("camera.list_media", {"fave": True, "all": True})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_get_camera_fave_list: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_post_camera_fave(request: web.Request):
  """Add a media file to favorites"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    body = await request.json()
  except Exception:
    return web.json_response({"error": "invalid body"}, status=400)

  file_type = body.get("type", "").strip()
  name = body.get("name", "").strip()

  if not file_type or not name:
    return web.json_response({"error": "type and name are required"}, status=400)

  try:
    response = await api_client.exec("camera.add_to_fave", {"type": file_type, "name": name})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=400)
    return web.json_response({"status": "ok"})
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_post_camera_fave: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_delete_camera_fave(request: web.Request):
  """Remove a media file from favorites"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    body = await request.json()
  except Exception:
    return web.json_response({"error": "invalid body"}, status=400)

  file_type = body.get("type", "").strip()
  name = body.get("name", "").strip()

  if not file_type or not name:
    return web.json_response({"error": "type and name are required"}, status=400)

  try:
    response = await api_client.exec("camera.remove_from_fave", {"type": file_type, "name": name})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=400)
    return web.json_response({"status": "ok"})
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_delete_camera_fave: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)
