import re

import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.socket.api import ApiMethod

_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


class MethodSetBleTarget(ApiMethod):
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    if not isinstance(args, dict):
      return {"status": "error", "error": "Wrong argument: expected object"}

    mac = args.get("mac")
    name = args.get("name")
    if not isinstance(mac, str) or not _MAC_RE.match(mac.strip()):
      return {"status": "error", "error": "invalid_mac"}

    target = {"mac": mac.strip().upper(), "name": name if isinstance(name, str) else None}
    m = self._plugin.ble_monitor
    was_active = bool(m and m.is_active())
    self._plugin.state.save({const.STATE_KEY_BLE_TARGET: target})
    now_active = bool(m and m.is_active())

    if m:
      await m.restart()

    if now_active and not was_active:
      await self._plugin.journal_beacon_active(True)

    return {"status": "ok", "data": {"target": target}}
