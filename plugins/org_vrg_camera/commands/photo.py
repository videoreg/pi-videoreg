import asyncio
import os
import shutil
from datetime import datetime

import plugins.org_vrg_http.functions as functions
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.gateway import Gateway, GatewayCommand, GatewayInteractions
from sdk.media_manager import MediaFileType


class CommandPhoto(GatewayCommand):
  """Take a photo. Args: [N] [night] — N is the camera number
  (1 or omitted = the built-in main camera, 2+ = paired rear cameras)."""

  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, gateway: Gateway, payload, args):
    number = 1
    is_night = False
    for token in (args or "").split() if isinstance(args, str) else []:
      if token == "night":
        is_night = True
      elif token.isdigit():
        number = int(token)

    if number >= 2:
      asyncio.create_task(self._take_rear_photo_and_send(gateway, payload, number))
      return

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

  async def _take_rear_photo_and_send(self, gateway: Gateway, payload, number: int):
    i18n = self._plugin.runner.i18n
    try:
      response = await self._plugin.api_client.exec(
        "rearcam.get_photo", {"number": number}, timeout=30
      )
    except Exception as e:
      self._plugin.logger.error(f"rearcam.get_photo failed: {e}", exc_info=True)
      await gateway.send_text(payload, i18n.t("rearcam.photo_failed", n=number))
      return

    if not response.is_ok():
      error = response.get_error()
      if error == "camera_not_found":
        text = i18n.t("rearcam.photo_camera_not_found", n=number)
      else:
        text = i18n.t("rearcam.photo_failed", n=number)
      await gateway.send_text(payload, text)
      return

    path = response.get_data().get("path")
    self._save_rear_photo_to_fave(path, number)
    # The file is left on disk on purpose: bot.send_image reads it
    # asynchronously after this command returns. The rearcam plugin reaps
    # stale rear_photo_*.jpg on the next take_photo call.
    if gateway.support(GatewayInteractions.IMAGE.value):
      await gateway.send_image(payload, path)
    else:
      await gateway.send_text(payload, path)

  def _save_rear_photo_to_fave(self, path: str, number: int):
    """Copies the rear-camera photo to the favorites folder and registers it."""
    try:
      name = f"{datetime.today().strftime('%Y-%m-%d_%H-%M-%S')}_rear{number}.jpg"
      dst = self._plugin.runner.videoreg.jpeg_fave_path(name)
      shutil.copy2(path, str(dst))
      self._plugin.runner.media_manager.append_file(MediaFileType.JPEG_FAVE, name)
    except (OSError, PermissionError) as e:
      self._plugin.logger.error(f"rear photo fave copy failed: {e}")
