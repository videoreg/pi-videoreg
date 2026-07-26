import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.socket.api import ApiMethod


class MethodGetBleConfig(ApiMethod):
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    m = self._plugin.ble_monitor
    active = bool(m and m.is_active())
    return {
      "status": "ok",
      "data": {
        "supported": bool(m and m.is_supported()),
        "enabled": bool(self._plugin.state.get(const.STATE_KEY_BLE_ENABLED, False)),
        "target": m.target() if m else None,
        "present": bool(m.is_present()) if active else None,
        "last_seen_seconds": m.last_seen_seconds() if active else None,
        "grace_minutes": m.grace_minutes() if m else const.BLE_GRACE_MINUTES_DEFAULT,
      },
    }
