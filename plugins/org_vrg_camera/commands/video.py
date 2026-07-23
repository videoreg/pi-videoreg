import asyncio
import os
from pathlib import Path

import plugins.org_vrg_http.functions as functions
from plugins.org_vrg_camera.convert import convert_h264_to_mp4
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.gateway import Gateway, GatewayCommand, GatewayInteractions
from sdk.media_manager import MediaFileType

DEFAULT_DURATION = 10


class CommandVideo(GatewayCommand):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, gateway: Gateway, payload, args):
    duration = int(args) if args else DEFAULT_DURATION

    await self._plugin.suspend_video()

    await gateway.send_text(payload, f"Take {duration}s video...")

    asyncio.create_task(self._take_video_and_send(gateway, payload, duration))

  async def _take_video_and_send(self, gateway: Gateway, payload, duration: int):
    if gateway.support(GatewayInteractions.STATUS.value):
      await gateway.send_status(payload, "record_video")

    try:
      path = await self._plugin.take_video(duration)
    except TimeoutError:
      self._plugin.logger.error("Take video timeout")
      path = None

    if not path:
      self._plugin.logger.error("take_video returned None")
      await gateway.send_text(payload, text="Error while taking a video")
      return

    name = os.path.basename(path).rsplit(".", 1)[0]
    h264_path = Path(path)
    mp4_path = self._plugin.runner.videoreg.mp4_path(f"{name}.mp4")

    await convert_h264_to_mp4(self._plugin, h264_path, mp4_path)
    self._plugin.copy_to_fave(name, MediaFileType.H264_FAVE)

    await self._plugin.continue_video()

    if gateway.support(GatewayInteractions.VIDEO.value):
      await gateway.send_video(payload, str(mp4_path), 1920, 1080)
    else:
      link = await functions.get_link(dir="video", file_name=name)
      await gateway.send_text(payload, link)

    # try:
    #   link = await functions.get_link(dir="video", file_name=name)

    #   response: ApiResponse = await self._plugin.api_client.exec(
    #     "bot.send_video",
    #     {
    #       "file_path": str(mp4_path),
    #       "fallback_message": f"Failed to send video. Use link instead:\n\n{link}"
    #     }
    #   )

    #   if not response.is_ok():
    #     self._plugin.logger.error(f"bot.send_video error: {response.get_error()}")
    #     return

    #   self._plugin.logger.info(f"mp4 sent to bot: {mp4_path}")
    # except RequestTimeoutError:
    #   self._plugin.logger.error("bot.send_video timeout")
