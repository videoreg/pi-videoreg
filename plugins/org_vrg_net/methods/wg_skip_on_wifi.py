import plugins.org_vrg_net.const as const
from plugins.org_vrg_net.plugin import NetPlugin
from sdk.socket.api import ApiMethod


class MethodWgSkipOnWifi(ApiMethod):
  """Persists the "don't connect while WiFi client is active" preference and
  applies it to the running monitor. Only saves the setting — it does not bring
  the interface up or down by itself.
  """

  _plugin: NetPlugin

  def __init__(self, plugin: NetPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    enable = bool(args.get("enabled")) if isinstance(args, dict) else args == "enable"

    self._plugin.state.save({const.KEY_WG_SKIP_ON_WIFI: enable})

    if self._plugin.wg_monitor:
      self._plugin.wg_monitor.skip_on_wifi = enable

    return {"status": "ok", "data": {"skip_on_wifi": enable}}
