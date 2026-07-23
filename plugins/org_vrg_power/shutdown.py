import time
from datetime import UTC, datetime, timedelta
from logging import Logger

from sdk.power import ChargingStatus, PowerSupply
from sdk.power.pisugar import PiSugar
from sdk.videoreg import Videoreg


class ShutdownConfig:
  reason: str = None
  wakeup: str = None
  wakeup_alarm_time: datetime = None
  wakeup_alarm_enabled: bool = False
  wakeup_on_power_restore_enabled: bool = False
  previous: "ShutdownConfig"

  @staticmethod
  def from_json(json: dict) -> "ShutdownConfig":
    if not json:
      return None
    config = ShutdownConfig()
    config.reason = str(json.get("reason", None))
    wakeup_alarm_time_str = str(json.get("wakeup_alarm_time", None))
    wakeup_alarm_time: datetime = None
    if wakeup_alarm_time_str and wakeup_alarm_time_str != "none":
      wakeup_alarm_time = datetime.fromisoformat(wakeup_alarm_time_str)
    config.wakeup_alarm_time = wakeup_alarm_time
    config.wakeup_alarm_enabled = bool(json.get("wakeup_alarm_enabled", False))
    config.wakeup_on_power_restore_enabled = bool(json.get("wakeup_on_power_restore_enabled", None))
    return config

  def to_json(self) -> dict:
    if self.wakeup_alarm_time:
      wakeup_alarm_time_str = self.wakeup_alarm_time.isoformat()
    else:
      wakeup_alarm_time_str = "none"

    return {
      "reason": self.reason,
      "wakeup_alarm_time": wakeup_alarm_time_str,
      "wakeup_alarm_enabled": self.wakeup_alarm_enabled,
      "wakeup_on_power_restore_enabled": self.wakeup_on_power_restore_enabled,
    }

  def verify(self) -> bool:
    if self.wakeup_alarm_time:
      current_time = datetime.now(UTC).astimezone()
      if self.wakeup_alarm_time <= current_time:
        return False
      elif (
        self.previous
        and self.previous.wakeup_alarm_time
        and self.wakeup_alarm_time <= self.previous.wakeup_alarm_time
      ):
        return False
    return True


class ShutdownLogic:
  last_attempt_shutdown_timestamp: int

  async def should_shutdown(self, charging_status: ChargingStatus) -> bool:
    raise NotImplementedError()


class ShutdownController:
  _videoreg: Videoreg
  _power_supply: PowerSupply
  _logger: Logger
  _shutdown_logic: ShutdownLogic
  _previous_config: ShutdownConfig

  def __init__(
    self,
    videoreg: Videoreg,
    power_supply: PowerSupply,
    logger: Logger,
    shutdown_logic: ShutdownLogic,
    previous_config: ShutdownConfig,
  ):
    self._videoreg = videoreg
    self._power_supply = power_supply
    self._logger = logger
    self._shutdown_logic = shutdown_logic
    self._previous_config = previous_config

  def get_wakeup_config(self):
    raise NotImplementedError()

  def _add_seconds_to_now(self, seconds) -> datetime:
    current_time = datetime.now(UTC).astimezone()
    new_time = current_time + timedelta(seconds=seconds + 5)  # +5 for _delayed_shutdown()
    return new_time

  async def shutdown(self, reason: str, force_wakeup_config: str = None) -> ShutdownConfig:

    self._shutdown_logic.last_attempt_shutdown_timestamp = time.time()

    wakeup = force_wakeup_config
    if not wakeup:
      wakeup = self.get_wakeup_config()

    shutdown_config = ShutdownConfig()
    shutdown_config.reason = reason
    shutdown_config.wakeup = wakeup
    shutdown_config.wakeup_on_power_restore_enabled = True  # always
    shutdown_config.previous = self._previous_config

    if wakeup == "1m":
      shutdown_config.wakeup_alarm_enabled = True
      shutdown_config.wakeup_alarm_time = self._add_seconds_to_now(60)
    elif wakeup == "2m":
      shutdown_config.wakeup_alarm_enabled = True
      shutdown_config.wakeup_alarm_time = self._add_seconds_to_now(120)
    elif wakeup == "10m":
      shutdown_config.wakeup_alarm_enabled = True
      shutdown_config.wakeup_alarm_time = self._add_seconds_to_now(10 * 60)
    elif wakeup == "30m":
      shutdown_config.wakeup_alarm_enabled = True
      shutdown_config.wakeup_alarm_time = self._add_seconds_to_now(30 * 60)
    elif wakeup == "1h":
      shutdown_config.wakeup_alarm_enabled = True
      shutdown_config.wakeup_alarm_time = self._add_seconds_to_now(3600)
    else:  # disabled/on-power-restore
      shutdown_config.wakeup_alarm_enabled = False

    if not shutdown_config.verify():
      self._logger.debug("shutdown_config not verified")
      return None

    config_applied = await self._apply_shutdown_config(shutdown_config)
    if not config_applied:
      return None

    await self._log_shutdown(shutdown_config)

    return shutdown_config

  async def _apply_shutdown_config(self, shutdown_config: ShutdownConfig) -> bool:
    if not isinstance(self._power_supply, PiSugar):
      return True  # no hardware alarm, just persist the state
    if shutdown_config.wakeup_alarm_time:
      wakeup_alarm_time_str = shutdown_config.wakeup_alarm_time.isoformat()
      new_time_str = await self._power_supply.set_alarm_wakeup_time(wakeup_alarm_time_str, weekday=127)
      if not new_time_str:
        self._logger.warning(f"pisugar bad alarm wakeup time: {new_time_str}")
        return False
      cur_time = datetime.now()
      new_time = datetime.fromisoformat(new_time_str)
      if not new_time or new_time.timestamp() < cur_time.timestamp():
        self._logger.warning(
          f"pisugar alarm wakeup time is less than current time: pisugar={new_time_str} current={cur_time}"
        )
        return False

    await self._power_supply.set_wakeup_on_power_restore(shutdown_config.wakeup_on_power_restore_enabled)
    await self._power_supply.set_alarm_wakeup_enabled(shutdown_config.wakeup_alarm_enabled)

    return True

  async def _log_shutdown(self, shutdown_config: ShutdownConfig):
    pass


# Keep old name as alias for any code that may reference it directly
PisugarShutdownController = ShutdownController
