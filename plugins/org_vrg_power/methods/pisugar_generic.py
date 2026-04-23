from sdk.pisugar import PiSugar
from sdk.socket.api import ApiMethod


class MethodPisugarGeneric(ApiMethod):
  _command: str
  _pisugar: PiSugar

  def __init__(self, pisugar: PiSugar, command: str):
    super().__init__()
    self._command = command
    self._pisugar = pisugar

  async def exec(self, args):
    if self._command == "get_charging_status":
      result = await self._pisugar.get_charging_status_slow_but_safe()
      return {"status": "ok", "bot_message": result}
    elif self._command == "get_bat_level":
      result = await self._pisugar.get_battery_percent()
      return {"status": "ok", "bot_message": result}
    elif self._command == "get_temp":
      result = await self._pisugar.get_temp()
      return {"status": "ok", "bot_message": result}
