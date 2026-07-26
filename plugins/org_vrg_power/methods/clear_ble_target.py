import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.socket.api import ApiMethod


class MethodClearBleTarget(ApiMethod):
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    self._plugin.state.save({const.STATE_KEY_BLE_TARGET: None})

    m = self._plugin.ble_monitor
    if m:
      await m.stop()

    return {"status": "ok", "data": {"target": None}}
