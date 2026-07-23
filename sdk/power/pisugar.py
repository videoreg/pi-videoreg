import asyncio
from asyncio.subprocess import Process
from logging import Logger
from typing import Any

from sdk.power.base import ChargingStatus, PowerSupply
from sdk.videoreg import Videoreg


class CommandResult:
  """Return value from a shell command: returncode, stdout, stderr."""

  returncode: int
  stdout: Any
  stderr: Any


class PiSugar(PowerSupply):
  """Communicates with the PiSugar battery board via shell scripts."""

  name = "pisugar"
  title = "PiSugar 3"
  battery_telemetry = True

  _videoreg: Videoreg
  _logger: Logger

  def __init__(self, videoreg: Videoreg, logger: Logger):
    self._videoreg = videoreg
    self._logger = logger

  async def _exec_pisugar_command(self, command) -> CommandResult:
    script_path = self._videoreg.app_path("task/pisugar.sh")

    cmd = ["bash", str(script_path), *command]

    process: Process = await asyncio.create_subprocess_exec(
      *cmd,
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    result = CommandResult()

    result.returncode = process.returncode
    result.stdout = stdout.decode()
    result.stderr = stderr.decode()

    return result

  async def get_battery_percent(self) -> int | None:
    result = await self._exec_pisugar_command(["get_bat_level"])
    if result.returncode == 0:
      return int(result.stdout.rstrip())
    else:
      return None

  async def get_charging_status(self) -> ChargingStatus:
    result = await self._exec_pisugar_command(["get_charging_status"])
    if result.returncode == 0:
      raw = result.stdout.rstrip()
      if raw == "true":
        return ChargingStatus.CHARGING
      elif raw == "false":
        return ChargingStatus.NOT_CHARGING
      else:
        return ChargingStatus.UNKNOWN
    else:
      return ChargingStatus.UNKNOWN

  async def get_charging_status_slow_but_safe(self) -> ChargingStatus:
    """Get charging status assuming PiSugar can return wrong status.
    If NOT_CHARGING first, wait 1s and doublecheck."""
    charging_status = await self.get_charging_status()
    if charging_status == ChargingStatus.NOT_CHARGING:
      await asyncio.sleep(1)
      second_check = await self.get_charging_status()
      if second_check != ChargingStatus.NOT_CHARGING:
        self._logger.warning("pisugar: charging status lies")
      charging_status = second_check

    return charging_status

  async def get_temp(self):
    result = await self._exec_pisugar_command(["get_temp"])
    if result.returncode == 0:
      return result.stdout.rstrip()
    else:
      return -1

  async def get_alarm_wakeup_enabled(self) -> bool:
    result = await self._exec_pisugar_command(["get_alarm_wakeup_enabled"])
    if result.returncode == 0:
      return True if result.stdout.rstrip() == "true" else False
    else:
      return False

  async def set_alarm_wakeup_enabled(self, enabled: bool) -> bool:
    enabled_param = "1" if enabled else "0"
    result = await self._exec_pisugar_command(["set_alarm_wakeup_enabled", enabled_param])
    if result.returncode == 0:
      return True if result.stdout.rstrip() == "ok" else False
    else:
      return False

  async def get_wakeup_on_power_restore(self) -> bool:
    result = await self._exec_pisugar_command("get_wakeup_on_power_restore")
    if result.returncode == 0:
      return True if result.stdout.rstrip() == "true" else False
    else:
      return False

  async def set_wakeup_on_power_restore(self, enabled: bool) -> bool:
    enabled_param = "1" if enabled else "0"
    result = await self._exec_pisugar_command(["set_wakeup_on_power_restore", enabled_param])
    if result.returncode == 0:
      return True if result.stdout.rstrip() == "ok" else False
    else:
      return False

  async def get_alarm_wakeup_time(self) -> str:
    result = await self._exec_pisugar_command(["get_alarm_wakeup_time"])
    if result.returncode == 0:
      return result.stdout.rstrip()
    else:
      return None

  async def set_alarm_wakeup_time(self, isodatetime: str, weekday: int) -> str:
    result = await self._exec_pisugar_command(["set_alarm_wakeup_time", isodatetime, str(weekday)])
    if result.returncode == 0:
      return result.stdout.rstrip()
    else:
      return None

  async def get_alarm_wakeup_weekday(self) -> str:
    result = await self._exec_pisugar_command(["get_alarm_wakeup_weekday"])
    if result.returncode == 0:
      return result.stdout.rstrip()
    else:
      return None

  async def get_charging_protection(self) -> bool:
    result = await self._exec_pisugar_command("get_charging_protection")
    if result.returncode == 0:
      return True if result.stdout.rstrip() == "true" else False
    else:
      return False

  async def set_charging_protection(self, enabled: bool) -> bool:
    enabled_param = "1" if enabled else "0"
    result = await self._exec_pisugar_command(["set_charging_protection", enabled_param])
    if result.returncode == 0:
      return True if result.stdout.rstrip() == "ok" else False
    else:
      return False

  async def shutdown(self) -> bool:
    result = await self._exec_pisugar_command(["shutdown"])

    if result.returncode == 0:
      return True
    else:
      return False
