from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.power import ChargingStatus, PowerSupply
from sdk.power.pisugar import PiSugar
from sdk.socket.api import ApiMethod


class MethodGetStatusText(ApiMethod):
  """Returns a short human-readable power status for the `/status` bot summary."""

  _power_supply: PowerSupply
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin, power_supply: PowerSupply):
    super().__init__()
    self._plugin = plugin
    self._power_supply = power_supply

  async def exec(self, args):
    try:
      charging_status = await self._power_supply.get_charging_status()
      charging = charging_status == ChargingStatus.CHARGING

      battery_percent = await self._power_supply.get_battery_percent()
      battery_str = f"{battery_percent}%" if battery_percent is not None else "unknown"
      if charging:
        battery_str += " (charging)"

      temp = await self._power_supply.get_temp() if isinstance(self._power_supply, PiSugar) else None
      temp_str = f"\nTemp: {temp}" if temp is not None else ""

      text = (
        f"Power: {self._power_supply.title}\n"
        f"Battery: {battery_str}{temp_str}\n"
        f"Uptime: {self._format_uptime(self._plugin.get_uptime())}"
      )

      return {"status": "ok", "data": {"text": text}}
    except Exception as e:
      self._plugin.logger.error(f"Error in get_status_text: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}

  @staticmethod
  def _format_uptime(uptime_sec: int) -> str:
    if uptime_sec < 60:
      return f"{uptime_sec}s"
    if uptime_sec < 3600:
      return f"{uptime_sec // 60}m {uptime_sec % 60}s"
    return f"{uptime_sec // 3600}h {uptime_sec % 3600 // 60}m"
