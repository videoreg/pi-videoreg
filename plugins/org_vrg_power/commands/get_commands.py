import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.interface import Interface, InterfaceCommand
from sdk.power import ChargingStatus, PowerSupply
from sdk.power.pisugar import PiSugar


class CommandGetCommands(InterfaceCommand):
  _power_supply: PowerSupply
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin, power_supply: PowerSupply):
    super().__init__()
    self._plugin = plugin
    self._power_supply = power_supply

  async def exec(self, interface: Interface, payload, args):
    wakeup_value = self._plugin.state.get(const.STATE_KEY_WAKEUP, None)
    wakeup_message = wakeup_value if wakeup_value else "disabled"
    
    charging_status = await self._power_supply.get_charging_status()
    charging_status_str = "yes" if charging_status == ChargingStatus.CHARGING else "no"
    
    battery_percent = await self._power_supply.get_battery_percent()
    battery_str = f"\nBattery: {battery_percent}%" if battery_percent is not None else ""
    
    temp = await self._power_supply.get_temp() if isinstance(self._power_supply, PiSugar) else None
    temp_str = f"\nTemp: {temp}" if temp is not None else ""
    
    uptime_sec = self._plugin.get_uptime()
    if uptime_sec < 60:
      uptime = f"{uptime_sec}s"
    elif uptime_sec < 3600:
      uptime = f"{uptime_sec // 60}m {uptime_sec % 60}s"
    else:
      uptime = f"{uptime_sec // 3600}h {uptime_sec % 3600 // 60}m"

    await interface.send_text(
      payload=payload,
      text=f"Power: {self._power_supply.title}\n\nCharging: {charging_status_str}{battery_str}{temp_str}\n\nUptime: {uptime}",
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
