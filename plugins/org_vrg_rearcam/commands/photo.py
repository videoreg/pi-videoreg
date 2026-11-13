from plugins.org_vrg_rearcam.plugin import RearcamPlugin
from sdk.gateway import Gateway, GatewayCommand, GatewayInteractions


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

    if not self._plugin.runner.media_manager.save_jpeg_to_fave(path):
      self._plugin.logger.error("rear photo fave copy failed: no free name")
    # The file is left on disk on purpose: bot.send_image reads it
    # asynchronously after this command returns. The plugin reaps stale
    # rear_photo_*.jpg on the next take_photo call.
    if gateway.support(GatewayInteractions.IMAGE.value):
      await gateway.send_image(payload, path)
    else:
      await gateway.send_text(payload, path)
