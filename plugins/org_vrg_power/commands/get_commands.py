import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.interface import Interface, InterfaceCommand
from sdk.pisugar import PiSugar


class CommandGetCommands(InterfaceCommand):
  _pisugar: PiSugar
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin, pisugar: PiSugar):
    super().__init__()
    self._plugin = plugin
    self._pisugar = pisugar

  async def exec(self, interface: Interface, payload, args):
    wakeup_value = self._plugin.state.get(const.STATE_KEY_WAKEUP, None)
    wakeup_message = wakeup_value if wakeup_value else "disabled"
    charging_status = await self._pisugar.get_charging_status()
    charging_status_str = "yes" if charging_status == 1 else "no"
    battery_percent = await self._pisugar.get_battery_percent()
    temp = await self._pisugar.get_temp()
    uptime_sec = self._plugin.get_uptime()
    if uptime_sec < 60:
      uptime = f"{uptime_sec}s"
    elif uptime_sec < 3600:
      uptime = f"{uptime_sec // 60}m {uptime_sec % 60}s"
    else:
      uptime = f"{uptime_sec // 3600}h {uptime_sec % 3600 // 60}m"

    await interface.send_text(
      payload=payload,
      text=f"Power:\n\nPiSugar charging: {charging_status_str}\nPiSugar battery: {battery_percent}%\nPiSugar temp: {temp}\n\nUptime: {uptime}",
      keyboard=[
        [
          {
            "text": f"Change wakeup config ({wakeup_message})",
            "callback_data": "command__power__wakeup_commands",
          }
        ],
        [
          {
            "text": "Shutdown (wakeup on power restore)",
            "callback_data": "command__power__shutdown__manual",
          }
        ],
        [{"text": "Reboot", "callback_data": "command__power__reboot"}],
      ],
    )
