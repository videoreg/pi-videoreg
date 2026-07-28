import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.socket.api import ApiMethod


class MethodSetBleEnabled(ApiMethod):
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    if isinstance(args, dict):
      args = args.get("enabled")
    if not isinstance(args, bool):
      return {"status": "error", "error": "Wrong argument: expected bool"}

    m = self._plugin.ble_monitor
    was_active = bool(m and m.is_active())
    self._plugin.state.save({const.STATE_KEY_BLE_ENABLED: args})
    now_active = bool(m and m.is_active())

    if m:
      # start() begins a fresh session: is_lost() applies only the short discovery
      # window until the beacon is first heard, so enabling with the beacon in range
      # settles to "present" within one window and never shuts down prematurely.
      if now_active and not was_active:
        await m.start()
      elif was_active and not now_active:
        await m.stop()

    if now_active != was_active:
      await self._plugin.journal_beacon_active(now_active)

    return {"status": "ok", "data": {"enabled": args}}
