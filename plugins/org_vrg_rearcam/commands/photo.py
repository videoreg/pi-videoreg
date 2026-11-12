import shutil
from datetime import datetime, timedelta

from plugins.org_vrg_rearcam.plugin import RearcamPlugin
from sdk.gateway import Gateway, GatewayCommand, GatewayInteractions
from sdk.media_manager import MediaFileType


class CommandPhoto(GatewayCommand):
  """Take a photo from rear camera #N.

  Instances are registered dynamically as `photo_N` commands, one per paired
  rear camera (see RearcamPlugin.sync_gateway_commands), so the bot menu shows
  an explicit entry for every camera.
  """

  _plugin: RearcamPlugin

  def __init__(self, plugin: RearcamPlugin, number: int):
    super().__init__()
    self._plugin = plugin
    self._number = number

  async def exec(self, gateway: Gateway, payload, args):
    i18n = self._plugin.runner.i18n
    try:
      path = await self._plugin.take_photo(self._number)
    except Exception as e:
      self._plugin.logger.error(f"photo_{self._number} failed: {e}", exc_info=True)
      if str(e) == "camera_not_found":
        text = i18n.t("rearcam.photo_camera_not_found", n=self._number)
      else:
        text = i18n.t("rearcam.photo_failed", n=self._number)
      await gateway.send_text(payload, text)
      return

    self._save_to_fave(path)
    # The file is left on disk on purpose: bot.send_image reads it
    # asynchronously after this command returns. The plugin reaps stale
    # rear_photo_*.jpg on the next take_photo call.
    if gateway.support(GatewayInteractions.IMAGE.value):
      await gateway.send_image(payload, path)
    else:
      await gateway.send_text(payload, path)

  def _save_to_fave(self, path: str):
    """Copies the rear-camera photo to the favorites folder and registers it.

    The name must match DATE_FORMAT (`%Y-%m-%d_%H-%M-%S`) — list_media skips
    unparseable names. On a same-second collision with a main-camera shot the
    timestamp is bumped by a second until free.
    """
    try:
      dt = datetime.today()
      vr = self._plugin.runner.videoreg
      for _ in range(10):
        name = dt.strftime("%Y-%m-%d_%H-%M-%S")
        dst = vr.jpeg_fave_path(f"{name}.jpg")
        if not dst.exists():
          break
        dt += timedelta(seconds=1)
      else:
        self._plugin.logger.error("rear photo fave copy failed: no free name")
        return
      shutil.copy2(path, str(dst))
      self._plugin.runner.media_manager.append_file(MediaFileType.JPEG_FAVE, f"{name}.jpg")
    except (OSError, PermissionError) as e:
      self._plugin.logger.error(f"rear photo fave copy failed: {e}")
