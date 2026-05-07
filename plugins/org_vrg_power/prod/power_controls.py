from plugins.org_vrg_power.power_controls import PowerControls
from sdk.helper import stream_subprocess

class PowerControlsImpl(PowerControls):
  async def start_charging_target(self):
    await stream_subprocess(
      cmd=["systemctl", "start", "vrg-charging.target"],
      start_cb=lambda pid, cmd: self._logger.debug(f"CMD (pid={pid}): {cmd}"),
      stdout_cb=lambda pid, s: self._logger.debug(f"STDOUT (pid={pid}): {s}"),
      stderr_cb=lambda pid, s: self._logger.debug(f"STDERR (pid={pid}): {s}")
      )
    
  async def stop_charging_target(self):
    await stream_subprocess(
      cmd=["systemctl", "stop", "vrg-charging.target"],
      start_cb=lambda pid, cmd: self._logger.debug(f"CMD (pid={pid}): {cmd}"),
      stdout_cb=lambda pid, s: self._logger.debug(f"STDOUT (pid={pid}): {s}"),
      stderr_cb=lambda pid, s: self._logger.debug(f"STDERR (pid={pid}): {s}")
      )