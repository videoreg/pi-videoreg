from sdk.power import ChargingStatus, PowerSupply
from sdk.power.pisugar import PiSugar
from sdk.socket.api import ApiMethod


class MethodPowerStatusGeneric(ApiMethod):
  _command: str
  _power_supply: PowerSupply

  def __init__(self, power_supply: PowerSupply, command: str):
    super().__init__()
    self._command = command
    self._power_supply = power_supply

  async def exec(self, args):
    if self._command == "get_charging_status":
      result = await self._power_supply.get_charging_status_slow_but_safe()
      return {"status": "ok", "bot_message": result.value}
    elif self._command == "get_bat_level":
      result = await self._power_supply.get_battery_percent()
      return {"status": "ok", "bot_message": result}
    elif self._command == "get_temp":
      if isinstance(self._power_supply, PiSugar):
        result = await self._power_supply.get_temp()
      else:
        result = None
      return {"status": "ok", "bot_message": result}
