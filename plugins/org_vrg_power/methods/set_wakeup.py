import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.pisugar import PiSugar
from sdk.socket.api import ApiMethod


class MethodSetWakeup(ApiMethod):
  _plugin: PowerPlugin
  _pisugar: PiSugar

  def __init__(self, plugin: PowerPlugin, pisugar: PiSugar):
    super().__init__()
    self._plugin = plugin
    self._pisugar = pisugar

  async def exec(self, args):
    verified_value = None

    if args == "1m":
      verified_value = "1m"
    elif args == "2m":
      verified_value = "2m"
    elif args == "10m":
      verified_value = "10m"
    elif args == "30m":
      verified_value = "30m"
    elif args == "1h":
      verified_value = "1h"
    elif args == "on-power-restore":
      verified_value = "on-power-restore"
    elif args == "disabled":
      verified_value = None
      await self._pisugar.set_alarm_wakeup_enabled(False)
    else:
      return {"status": "error", "error": "Wrong argument"}

    self._plugin.state.save({const.STATE_KEY_WAKEUP: verified_value})

    return {"status": "ok", "new_value": args}
