import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.socket.api import ApiMethod


class MethodSetBleGrace(ApiMethod):
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    if isinstance(args, dict):
      args = args.get("minutes")
    try:
      minutes = int(args)
    except (TypeError, ValueError):
      return {"status": "error", "error": "Wrong argument: expected integer minutes"}

    if minutes < const.BLE_GRACE_MINUTES_MIN or minutes > const.BLE_GRACE_MINUTES_MAX:
      return {"status": "error", "error": "out_of_range"}

    self._plugin.state.save({const.STATE_KEY_BLE_GRACE_MINUTES: minutes})

    return {"status": "ok", "data": {"grace_minutes": minutes}}
