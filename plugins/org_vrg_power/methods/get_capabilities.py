from sdk.power import PowerSupply
from sdk.power.pisugar import PiSugar
from sdk.socket.api import ApiMethod


class MethodGetCapabilities(ApiMethod):
  _power_supply: PowerSupply

  def __init__(self, power_supply: PowerSupply):
    super().__init__()
    self._power_supply = power_supply

  async def exec(self, args):
    is_pisugar = isinstance(self._power_supply, PiSugar)
    return {
      "status": "ok",
      "data": {
        "name": self._power_supply.name,
        "title": self._power_supply.title,
        "battery_telemetry": self._power_supply.battery_telemetry,
        "alarm_wakeup": is_pisugar,
        "charging_protection": is_pisugar,
        "hw_shutdown": is_pisugar,
      },
    }
