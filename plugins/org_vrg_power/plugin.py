import asyncio
import subprocess
import time
from datetime import UTC, datetime

import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.power_controls import PowerControls
from plugins.org_vrg_power.shutdown import PisugarShutdownController, ShutdownLogic
from sdk.helper import stream_subprocess
from sdk.keep_alive import KeepAlive
from sdk.service import Plugin


class PowerPlugin(Plugin):
  _time_start: int
  _last_charging_status: int = None
  _shutdown_logic: ShutdownLogic
  _shutdown_controller: PisugarShutdownController
  _power_controls: PowerControls
  keep_alive: KeepAlive

  def __init__(self, id, name, runner):
    super().__init__(id, name, runner)
    self._time_start = time.time()
    self.keep_alive = KeepAlive()

  def get_uptime(self):
    return int(time.time() - self._time_start)

  async def start(self):
    await super().start()
    # await self._configure_governor()
    alarm_time = await self._is_alarm_wakeup_pending()
    if alarm_time:
      self.logger.info(f"alarm wakeup pending: {alarm_time.isoformat()}")
      self.keep_alive.have_to_wait("initial_power", 60)
    asyncio.create_task(self.runner.pisugar.set_alarm_wakeup_enabled(False))
    asyncio.create_task(self.runner.pisugar.set_wakeup_on_power_restore(True))
    asyncio.create_task(self._apply_charging_protection())
    asyncio.create_task(self._start_check_charging_loop())

  async def _apply_charging_protection(self):
    enabled = bool(self.state.get(const.STATE_KEY_CHARGING_PROTECTION, True))
    try:
      ok = await self.runner.pisugar.set_charging_protection(enabled)
      if ok:
        self.logger.info(f"charging protection applied: {enabled}")
      else:
        self.logger.warning(f"PiSugar rejected charging protection={enabled}")
    except Exception as e:
      self.logger.error(f"failed to apply charging protection: {e}", exc_info=True)

  async def delayed_shutdown(self):
    self.logger.info("shutdown")
    await self.runner.pisugar.shutdown()

  async def delayed_reboot(self):
    self.logger.info("reboot")
    subprocess.run(["sudo", "reboot"])

  def init_shutdown(
    self, shutdown_logic: ShutdownLogic, shutdown_controller: PisugarShutdownController
  ):
    self._shutdown_logic = shutdown_logic
    self._shutdown_controller = shutdown_controller

  def init_power_controls(self, power_controls: PowerControls):
    self._power_controls = power_controls

  # TODO: freq limited in config.txt
  # async def _configure_governor(self):
  #   await stream_subprocess(
  #     cmd=["echo", "powersave", "|", "sudo", "tee", "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"],
  #     start_cb=lambda pid, cmd: self.logger.debug(f"CMD (pid={pid}): {cmd}"),
  #     stdout_cb=lambda pid, s: self.logger.debug(f"STDOUT (pid={pid}): {s}"),
  #     stderr_cb=lambda pid, s: self.logger.debug(f"STDERR (pid={pid}): {s}")
  #     )
  #   self.logger.info("governor set to powersave")

  async def _is_alarm_wakeup_pending(self) -> datetime | None:
    try:
      if not await self.runner.pisugar.get_alarm_wakeup_enabled():
        return None
      alarm_time_str = await self.runner.pisugar.get_alarm_wakeup_time()
      if not alarm_time_str:
        return None
      alarm_time = datetime.fromisoformat(alarm_time_str)
      now = datetime.now(alarm_time.tzinfo or UTC)
      return alarm_time if alarm_time > now else None
    except Exception:
      return None

  async def _start_check_charging_loop(self):
    _initial_captured = False
    while self.runner.is_running():
      is_charging = await self.runner.pisugar.get_charging_status_slow_but_safe()

      if not _initial_captured:
        _initial_captured = True
        if is_charging == 1:
          self.keep_alive.have_to_wait("initial_power", 60)

      # be carefull: don't use continue here
      if is_charging != self._last_charging_status:
        if is_charging == -1:
          self.logger.info("Charging is off: will stop vrg-charging.target")
          await self._power_controls.stop_charging_target()
        else:
          self.logger.info("Charging is on: will start vrg-charging.target")
          await self._power_controls.start_charging_target()

      await asyncio.sleep(5)

      # shutdown after delay to prevent immediately shutdown

      if self._shutdown_logic and self._shutdown_controller:
        should_shutdown = await self._shutdown_logic.should_shutdown(is_charging)
        if should_shutdown:
          shutdown_config = await self._shutdown_controller.shutdown("stop_charging")
          if not shutdown_config:
            continue

          self.state.save({const.STATE_KEY_LAST_SHUTDOWN_CONFIG: shutdown_config.to_json()})

          asyncio.create_task(self.delayed_shutdown())
          break

      self._last_charging_status = is_charging
