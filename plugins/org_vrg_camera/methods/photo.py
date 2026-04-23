import asyncio
import os

from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.media_manager import MediaFileType
from sdk.socket.api import ApiMethod, ApiResponse
from sdk.socket.requests import RequestTimeoutError


class MethodPhoto(ApiMethod):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    args = args or {}
    if isinstance(args, str):
      args = {"mode": args}
    mode = args.get("mode")
    is_sync = bool(args.get("is_sync", False))
    is_screenshot = mode == "screenshot"
    is_night = mode == "night"

    await self._plugin.suspend_video()

    if is_sync:
      path = await self._plugin.take_photo(is_screenshot, is_night)
      name = os.path.basename(path).rsplit(".", 1)[0]
      if not is_screenshot:
        self._plugin.copy_to_fave(name, MediaFileType.JPEG_FAVE)
      await self._plugin.continue_video()

      return {"status": "ok", "data": {"name": name}}

    asyncio.create_task(self._take_photo_and_send(is_screenshot, is_night))
    return {"status": "ok"}

  async def _take_photo_and_send(self, is_screenshot: bool, is_night: bool):
    path = await self._plugin.take_photo(is_screenshot, is_night)
    name = os.path.basename(path).rsplit(".", 1)[0]
    if not is_screenshot:
      self._plugin.copy_to_fave(name, MediaFileType.JPEG_FAVE)
    await self._plugin.continue_video()

    try:
      response: ApiResponse = await self._plugin.api_client.exec(
        "bot.send_photo", {"file_path": path}
      )
      if not response.is_ok():
        self._plugin.logger.warning(f"bot.send_photo error: {response.get_error()}")
    except RequestTimeoutError:
      self._plugin.logger.warning("bot.send_photo timeout")
