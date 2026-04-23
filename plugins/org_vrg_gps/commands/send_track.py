from plugins.org_vrg_gps.plugin import GpsPlugin
from sdk.interface import Interface, InterfaceCommand, InterfaceInteractions


class CommandSendTrack(InterfaceCommand):
  _plugin: GpsPlugin

  def __init__(self, plugin: GpsPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, interface: Interface, payload, args):
    if not interface.support(InterfaceInteractions.DOCUMENT.value):
      await interface.send_text(payload, "Sending files not supported")
      return

    file_name = str(args)

    if not file_name:
      self._plugin.logger.warning(
        f"Command CommandSendTrack: missing file name in args args={args}"
      )
      return

    file_path = self._plugin.runner.videoreg.gps_path(f"{file_name}.gpx")

    if not file_path.exists():
      self._plugin.logger.warning(
        f"Command CommandSendTrack: file not exists file_name={file_name}"
      )
      return

    await interface.send_document(payload, str(file_path))

    # try:
    #   response: ApiResponse = await self._plugin.api_client.exec(
    #     "bot.send_document",
    #     {
    #       "file_path": str(file_path)
    #     })

    #   if not response.is_ok():
    #     self._plugin.logger.warning(f"bot.send_document error: {response.get_error()}")

    # except RequestTimeoutError:
    #   self._plugin.logger.warning("bot.send_document timeout")
