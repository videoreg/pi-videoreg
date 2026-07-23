import plugins.org_vrg_net.const as const
from plugins.org_vrg_net.plugin import NetPlugin
from sdk.socket.api import ApiMethod


class MethodGetWireguardSettings(ApiMethod):
  """Returns the current WireGuard switches: live interface state, auto-connect
  and the "skip while WiFi client is connected" preference."""

  _plugin: NetPlugin

  def __init__(self, plugin: NetPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    active = await self._plugin.wg_monitor.is_wg_active()
    auto = self._plugin.state.get(const.KEY_WG_AUTO, True)
    skip_on_wifi = self._plugin.state.get(const.KEY_WG_SKIP_ON_WIFI, True)

    return {
      "status": "ok",
      "data": {
        "active": active,
        "auto": auto,
        "skip_on_wifi": skip_on_wifi,
      },
    }
