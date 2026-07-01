from plugins.org_vrg_sms.plugin import SmsPlugin
from sdk.socket.api import ApiMethod


class MethodGetModemInfo(ApiMethod):
  """Returns modem info read directly over the AT port.

  Used as a fallback by net.modem_info for modems that ModemManager does not
  manage (e.g. the A7670 over RNDIS). The AT port is owned by the vrg-modem
  process, so this info can only be read here, not from the net plugin.
  """

  _plugin: SmsPlugin

  def __init__(self, plugin: SmsPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      result = await self._plugin.sms_manager.get_modem_info()
      return {"status": "ok", "data": result}
    except Exception as e:
      self._plugin.logger.error(f"Error getting modem info: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
