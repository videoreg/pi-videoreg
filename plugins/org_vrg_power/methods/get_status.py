import time

import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.methods.keep_alive import REASON as KEEP_ALIVE_REASON
from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.pisugar import PiSugar
from sdk.socket.api import ApiMethod


class MethodGetStatus(ApiMethod):
  _pisugar: PiSugar
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin, pisugar: PiSugar):
    super().__init__()
    self._plugin = plugin
    self._pisugar = pisugar

  def _get_keep_alive_seconds(self) -> int | None:
    reasons = self._plugin.keep_alive.get_alive_reasons()
    if KEEP_ALIVE_REASON in reasons:
      remaining = int(reasons[KEEP_ALIVE_REASON] - time.time())
      return max(0, remaining)
    return None

  async def exec(self, args):
    """Returns current power status: battery, charging, temperature, uptime."""
    try:
      charging_status = await self._pisugar.get_charging_status_slow_but_safe()
      battery_percent = await self._pisugar.get_battery_percent()
      temp = await self._pisugar.get_temp()

      return {
        "status": "ok",
        "data": {
          "charging": charging_status == 1,
          "battery_percent": battery_percent,
          "temp": temp,
          "uptime": self._plugin.get_uptime(),
          "wakeup": self._plugin.state.get(const.STATE_KEY_WAKEUP, None),
          "keep_alive_seconds": self._get_keep_alive_seconds(),
        },
      }
    except Exception as e:
      self._plugin.logger.error(f"Error in get_status: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
