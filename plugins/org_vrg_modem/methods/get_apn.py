from plugins.org_vrg_modem.plugin import ModemPlugin
from sdk.socket.api import ApiMethod


class MethodGetApn(ApiMethod):
  """Returns the modem's current APN, read over AT (AT+CGDCONT?)."""

  _plugin: ModemPlugin

  def __init__(self, plugin: ModemPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      apn = await self._plugin.modem.get_apn()
      if apn is None:
        return {"status": "error", "error": "Modem not available"}
      return {"status": "ok", "data": {"apn": apn}}
    except Exception as e:
      self._plugin.logger.error(f"Error getting apn: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
