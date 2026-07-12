from plugins.org_vrg_modem.plugin import ModemPlugin
from sdk.socket.api import ApiMethod


class MethodGetModemInfo(ApiMethod):
  """Returns modem info read directly over the AT port.

  Used as a fallback by net.modem_info for modems that ModemManager does not
  manage (e.g. the A7670 over RNDIS). The AT port is owned by the vrg-modem
  process, so this info can only be read here, not from the net plugin.

  Serves the value cached by the plugin's background poller so callers (the
  dashboard tile) never block on a slow AT read. The cache is only cold for the
  first poll after startup, where we fall back to a one-off live read.
  """

  _plugin: ModemPlugin

  def __init__(self, plugin: ModemPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      cached = self._plugin.modem_info
      if cached is not None:
        return {"status": "ok", "data": cached}

      # Cold cache (background poll hasn't produced a value yet) — read live once.
      result = await self._plugin.sms_manager.get_modem_info()
      return {"status": "ok", "data": result}
    except Exception as e:
      self._plugin.logger.error(f"Error getting modem info: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
