import asyncio
import os
from pathlib import Path

import plugins.org_vrg_http.functions as functions
from plugins.org_vrg_camera.convert import convert_h264_to_mp4
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.media_manager import MediaFileType
from sdk.socket.api import ApiMethod, ApiResponse
from sdk.socket.requests import RequestTimeoutError

DEFAULT_DURATION = 10


class MethodVideo(ApiMethod):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    args = args or {}
    if isinstance(args, str):
      args = {"duration": args}
    duration = int(args.get("duration", DEFAULT_DURATION))
    is_sync = bool(args.get("is_sync", False))

    await self._plugin.suspend_video()

    if is_sync:
      try:
        path = await self._plugin.take_video(duration)
      except TimeoutError:
        self._plugin.logger.error("Take video timeout")
        path = None

      if not path:
        return {"status": "error", "error": "take_video failed"}
      name = os.path.basename(path).rsplit(".", 1)[0]
      h264_path = Path(path)
      mp4_path = self._plugin.runner.videoreg.mp4_path(f"{name}.mp4")
      await convert_h264_to_mp4(self._plugin, h264_path, mp4_path)
      self._plugin.copy_to_fave(name, MediaFileType.H264_FAVE)
      await self._plugin.continue_video()

      return {"status": "ok", "data": {"name": name}}

    asyncio.create_task(self._take_video_and_send(duration))
    return {"status": "ok", "bot_message": f"Take {duration}s video..."}

  async def _take_video_and_send(self, duration: int):
    try:
      path = await self._plugin.take_video(duration)
    except TimeoutError:
      self._plugin.logger.error("Take video timeout")
      path = None

    if not path:
      self._plugin.logger.error("take_video returned None")
      return

    name = os.path.basename(path).rsplit(".", 1)[0]
    h264_path = Path(path)
    mp4_path = self._plugin.runner.videoreg.mp4_path(f"{name}.mp4")

    await convert_h264_to_mp4(self._plugin, h264_path, mp4_path)
    self._plugin.copy_to_fave(name, MediaFileType.H264_FAVE)
    await self._plugin.continue_video()

    try:
      link = await functions.get_link(dir="video", file_name=name)

      response: ApiResponse = await self._plugin.api_client.exec(
        "bot.send_video",
        {
          "file_path": str(mp4_path),
          "fallback_message": f"Failed to send video. Use link instead:\n\n{link}",
        },
      )

      if not response.is_ok():
        self._plugin.logger.error(f"bot.send_video error: {response.get_error()}")
        return

      self._plugin.logger.info(f"mp4 sent to bot: {mp4_path}")
    except RequestTimeoutError:
      self._plugin.logger.error("bot.send_video timeout")
