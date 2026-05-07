"""HTTP handlers for the Camera page"""

from aiohttp import web


async def handle_get_camera_info(request: web.Request):
  """Camera info: model, recording state, video size"""
  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("camera.get_info", {})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except Exception as e:
    logger.error(f"Error in handle_get_camera_info: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_get_camera_modes(request: web.Request):
  """List of available camera modes from rpicam-hello"""
  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("camera.get_camera_modes", {})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except Exception as e:
    logger.error(f"Error in handle_get_camera_modes: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_post_camera_settings(request: web.Request):
  """Save camera settings (fps, bitrate, camera_mode_str, width, height)"""
  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    body = await request.json()
    response = await api_client.exec("camera.set_video_settings", body)
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=400)
    return web.json_response(response.get_data())
  except Exception as e:
    logger.error(f"Error in handle_post_camera_settings: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_post_camera_photo(request: web.Request):
  """Synchronous photo capture, returns filename"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    body = await request.json()
    mode = body.get("mode", None)
    args = {"mode": mode, "is_sync": True}
    response = await api_client.exec("camera.photo", args, timeout=30.0)
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_post_camera_photo: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_post_camera_video_start(request: web.Request):
  """Start video recording"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("camera.video_start", {})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_post_camera_video_start: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_post_camera_video_pause(request: web.Request):
  """Pause video recording"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("camera.video_pause", {})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_post_camera_video_pause: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_post_camera_short_video(request: web.Request):
  """Synchronous short video capture, returns filename"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("camera.video", {"is_sync": True}, timeout=75.0)
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_post_camera_short_video: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_post_camera_stream_start(request: web.Request):
  """Switch camera to stream mode (RTSP + HLS)"""
  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("camera.stream_start", {}, timeout=30.0)
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except Exception as e:
    logger.error(f"Error in handle_post_camera_stream_start: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_post_camera_stream_stop(request: web.Request):
  """Switch camera back to file recording mode"""
  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("camera.stream_stop", {}, timeout=30.0)
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except Exception as e:
    logger.error(f"Error in handle_post_camera_stream_stop: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_post_camera_stream_settings(request: web.Request):
  """Save stream-specific settings (camera_mode_str, video_width, video_height)"""
  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    body = await request.json()
    response = await api_client.exec("camera.set_stream_settings", body)
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=400)
    return web.json_response(response.get_data())
  except Exception as e:
    logger.error(f"Error in handle_post_camera_stream_settings: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_get_camera_stream_status(request: web.Request):
  """Current stream state and HLS URL"""
  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("camera.stream_status", {})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    return web.json_response(response.get_data())
  except Exception as e:
    logger.error(f"Error in handle_get_camera_stream_status: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)
