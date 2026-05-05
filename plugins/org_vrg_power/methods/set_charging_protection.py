import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.pisugar import PiSugar
from sdk.socket.api import ApiMethod


class MethodSetChargingProtection(ApiMethod):
  _plugin: PowerPlugin
  _pisugar: PiSugar

  def __init__(self, plugin: PowerPlugin, pisugar: PiSugar):
    super().__init__()
    self._plugin = plugin
    self._pisugar = pisugar

  async def exec(self, args):
    if not isinstance(args, bool):
      return {"status": "error", "error": "Wrong argument: expected bool"}

    try:
      ok = await self._pisugar.set_charging_protection(args)
    except Exception as e:
      self._plugin.logger.error(f"set_charging_protection failed: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}

    if not ok:
      return {"status": "error", "error": "PiSugar rejected the command"}

    self._plugin.state.save({const.STATE_KEY_CHARGING_PROTECTION: args})
    return {"status": "ok", "data": {"enabled": args}}
