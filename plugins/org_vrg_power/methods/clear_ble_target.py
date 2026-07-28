import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.socket.api import ApiMethod


class MethodClearBleTarget(ApiMethod):
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    m = self._plugin.ble_monitor
    was_active = bool(m and m.is_active())
    self._plugin.state.save({const.STATE_KEY_BLE_TARGET: None})

    if m:
      await m.stop()

    if was_active:
      await self._plugin.journal_beacon_active(False)

    return {"status": "ok", "data": {"target": None}}
