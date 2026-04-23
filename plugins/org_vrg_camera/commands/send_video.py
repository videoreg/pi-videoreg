from pathlib import Path

import plugins.org_vrg_http.functions as functions
from plugins.org_vrg_camera.convert import convert_h264_to_mp4
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.interface import Interface, InterfaceCommand, InterfaceInteractions


class CommandSendVideo(InterfaceCommand):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, interface: Interface, payload, args):
    file_name = str(args)

    if not file_name:
      self._plugin.logger.warning(
        f"Command CommandSendVideo: missing file name in args args={args}"
      )
      return

    h264_file_path = self._plugin.runner.videoreg.h264_path(f"{file_name}.h264")

    if not h264_file_path.exists():
      self._plugin.logger.warning(
        f"Command CommandSendVideo: file not exists file_name={file_name}"
      )
      return

    mp4_file_name = f"{file_name}.mp4"
    mp4_file_path = self._plugin.runner.videoreg.mp4_path(mp4_file_name)

    if mp4_file_path.exists():
      self._plugin.logger.debug(f"mp4 exists will send: {mp4_file_path}")
      await self._send_mp4_to_bot(interface, payload, mp4_file_path, file_name)
    else:
      self._plugin.logger.debug(f"mp4 not exists will convert: {mp4_file_path}")
      await self._convert_and_send(interface, payload, h264_file_path, mp4_file_path, file_name)

    # return {"status": "ok"}

  async def _convert_and_send(
    self, interface: Interface, payload, h264_file_path: Path, mp4_file_path: Path, file_name: str
  ):
    await self._plugin.suspend_video()
    await convert_h264_to_mp4(self._plugin, h264_file_path, mp4_file_path)
    await self._plugin.continue_video()
    await self._send_mp4_to_bot(interface, payload, mp4_file_path, file_name)

  async def _send_mp4_to_bot(
    self, interface: Interface, payload, mp4_file_path: Path, file_name: str
  ):
    if interface.support(InterfaceInteractions.VIDEO.value):
      await interface.send_video(payload, str(mp4_file_path))
    else:
      link = await functions.get_link(dir="video", file_name=file_name)
      await interface.send_text(payload, link)
    # try:
    #   link = await functions.get_link(dir="video", file_name=file_name)

    #   response: ApiResponse = await self._plugin.api_client.exec(
    #     "bot.send_video",
    #     {
    #       "file_path": str(mp4_file_path),
    #       "fallback_message": f"Failed to send photo. Use link instead:\n\n{link}"
    #     }
    #   )

    #   if not response.is_ok():
    #     self._plugin.logger.error(f"bot.send_video error: {response.get_error()}")
    #     return

    #   self._plugin.logger.info(f"mp4 sent to bot: {mp4_file_path}")
    # except RequestTimeoutError:
    #   self._plugin.logger.error(f"bot.send_video timeout")
