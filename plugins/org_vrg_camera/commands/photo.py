import asyncio
import os

import plugins.org_vrg_http.functions as functions
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.gateway import Gateway, GatewayCommand, GatewayInteractions
from sdk.media_manager import MediaFileType


class CommandPhoto(GatewayCommand):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, gateway: Gateway, payload, args):
    is_night = args == "night"

    await self._plugin.suspend_video()

    asyncio.create_task(self._take_photo_and_send(gateway, payload, is_night))

  async def _take_photo_and_send(self, gateway: Gateway, payload, is_night: bool):
    path = await self._plugin.take_photo(is_screenshot=False, is_night=is_night)
    name = os.path.basename(path).rsplit(".", 1)[0]
    self._plugin.copy_to_fave(name, MediaFileType.JPEG_FAVE)
    await self._plugin.continue_video()

    if gateway.support(GatewayInteractions.IMAGE.value):
      await gateway.send_image(payload, path)
    else:
      link = await functions.get_link(dir="photo", file_name=name)
      await gateway.send_text(payload, link)
