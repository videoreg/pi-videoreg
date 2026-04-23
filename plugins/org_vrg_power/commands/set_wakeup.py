import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.interface import Interface, InterfaceCommand
from sdk.pisugar import PiSugar


class CommandSetWakeup(InterfaceCommand):
  _plugin: PowerPlugin
  _pisugar: PiSugar

  def __init__(self, plugin: PowerPlugin, pisugar: PiSugar):
    super().__init__()
    self._plugin = plugin
    self._pisugar = pisugar

  async def exec(self, interface: Interface, payload, args):
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
      self._plugin.logger.warning(f"Command CommandSetWakeup wrong argument {args}")
      return

    self._plugin.state.save({const.STATE_KEY_WAKEUP: verified_value})

    await interface.send_text(payload=payload, text=f"Did set to {verified_value}")
