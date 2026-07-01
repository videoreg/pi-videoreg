from plugins.org_vrg_modem.plugin import ModemPlugin
from sdk.socket.api import ApiMethod


class MethodSetApn(ApiMethod):
  """Sets the modem's APN over AT (AT+CGDCONT) and re-attaches the radio.

  An empty APN clears the context (operator/auto APN).
  """

  _plugin: ModemPlugin

  def __init__(self, plugin: ModemPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    if not isinstance(args, dict):
      return {"status": "error", "error": "Arguments should be JSON"}

    apn = args.get("apn", "")
    apn = apn.strip() if isinstance(apn, str) else ""

    try:
      ok = await self._plugin.modem.set_apn(apn)
      if not ok:
        return {"status": "error", "error": "Failed to set APN"}
      return {"status": "ok"}
    except Exception as e:
      self._plugin.logger.error(f"Error setting apn: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
