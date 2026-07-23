from pathlib import Path

import plugins.org_vrg_http.functions as functions
from plugins.org_vrg_camera.convert import convert_h264_to_mp4
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.gateway import Gateway, GatewayCommand


class CommandSendVideoLink(GatewayCommand):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, gateway: Gateway, payload, args):
    file_name = str(args)

    if not file_name:
      self._plugin.logger.warning(
        f"Command CommandSendVideoLink: missing file name in args args={args}"
      )
      return

    h264_file_path = self._plugin.runner.videoreg.h264_path(f"{file_name}.h264")

    if not h264_file_path.exists():
      self._plugin.logger.warning(
        f"Command CommandSendVideoLink: file not exists file_name={file_name}"
      )
      return

    mp4_file_name = f"{file_name}.mp4"
    mp4_file_path = self._plugin.runner.videoreg.mp4_path(mp4_file_name)

    if mp4_file_path.exists():
      self._plugin.logger.debug(f"mp4 exists will send: {mp4_file_path}")
      await self._send_message_to_bot(gateway, payload, file_name)
    else:
      self._plugin.logger.debug(f"mp4 not exists will convert: {mp4_file_path}")
      await self._convert_and_send(gateway, payload, file_name, h264_file_path, mp4_file_path)

    # return {"status": "ok", "bot_message": f"Converting {mp4_file_name}..."}

  async def _convert_and_send(
    self, gateway: Gateway, payload, file_name: str, h264_file_path: Path, mp4_file_path: Path
  ):
    await self._plugin.suspend_video()
    await convert_h264_to_mp4(self._plugin, h264_file_path, mp4_file_path)
    await self._plugin.continue_video()

    await self._send_message_to_bot(gateway, payload, file_name)

  async def _send_message_to_bot(self, gateway: Gateway, payload, file_name: str):
    link = await functions.get_link(dir="video", file_name=file_name)
    await gateway.send_text(payload, link)

    # try:
    #   link = await functions.get_link(dir="video", file_name=file_name)

    #   response: ApiResponse = await self._plugin.api_client.exec("bot.send_message", {"message": link})

    #   if not response.is_ok():
    #     self._plugin.logger.error(f"bot.send_video error: {response.get_error()}")
    #     return

    # except RequestTimeoutError:
    #   self._plugin.logger.error(f"bot.send_video timeout")
