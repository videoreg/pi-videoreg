import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.power import PowerSupply
from sdk.power.pisugar import PiSugar
from sdk.socket.api import ApiMethod


class MethodSetChargingProtection(ApiMethod):
  _plugin: PowerPlugin
  _power_supply: PowerSupply

  def __init__(self, plugin: PowerPlugin, power_supply: PowerSupply):
    super().__init__()
    self._plugin = plugin
    self._power_supply = power_supply

  async def exec(self, args):
    if not isinstance(args, bool):
      return {"status": "error", "error": "Wrong argument: expected bool"}

    if not isinstance(self._power_supply, PiSugar):
      return {"status": "error", "error": "feature_not_supported"}

    try:
      ok = await self._power_supply.set_charging_protection(args)
    except Exception as e:
      self._plugin.logger.error(f"set_charging_protection failed: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}

    if not ok:
      return {"status": "error", "error": "PiSugar rejected the command"}

    self._plugin.state.save({const.STATE_KEY_CHARGING_PROTECTION: args})
    return {"status": "ok", "data": {"enabled": args}}
