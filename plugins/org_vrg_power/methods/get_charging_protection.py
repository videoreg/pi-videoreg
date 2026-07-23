import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.socket.api import ApiMethod


class MethodGetChargingProtection(ApiMethod):
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    enabled = self._plugin.state.get(const.STATE_KEY_CHARGING_PROTECTION, True)
    return {"status": "ok", "data": {"enabled": bool(enabled)}}
