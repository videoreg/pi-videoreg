import asyncio
import json
import time
from logging import Logger

import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from plugins.org_vrg_power.shutdown import ShutdownController, ShutdownConfig, ShutdownLogic
from sdk.power import ChargingStatus, PowerSupply
from sdk.power.pisugar import PiSugar
from sdk.socket.api import ApiClient, ApiResponse
from sdk.videoreg import Videoreg


class ShutdownLogicImpl(ShutdownLogic):
  _videoreg: Videoreg
  _power_supply: PowerSupply
  _logger: Logger
  _api_client: ApiClient

  def __init__(self, videoreg: Videoreg, logger: Logger, power_supply: PowerSupply, api_client: ApiClient):
    self._videoreg = videoreg
    self._logger = logger
    self._power_supply = power_supply
    self._api_client = api_client
    self.last_attempt_shutdown_timestamp = 0

  async def should_shutdown(self, charging_status: ChargingStatus) -> bool:
    if charging_status == ChargingStatus.NOT_CHARGING:
      plugins_ready = await asyncio.gather(
        self._is_plugin_ready_to_die("bot"),
        self._is_plugin_ready_to_die("camera"),
        self._is_plugin_ready_to_die("sms"),
        self._is_plugin_ready_to_die("power"),
      )

      if not all(plugins_ready):
        return False

      # prevent shutdown in loop
      if self.last_attempt_shutdown_timestamp == 0:
        self.last_attempt_shutdown_timestamp = time.time()
        return True
      else:
        return time.time() - self.last_attempt_shutdown_timestamp > 30

    else:
      self.last_attempt_shutdown_timestamp = 0

    return False

  async def _is_plugin_ready_to_die(self, plugin_name: str) -> bool:
    try:
      response: ApiResponse = await self._api_client.exec(f"{plugin_name}.is_ready_to_die", None)

      if not response.is_ok():
        self._logger.warning(f"plugin {plugin_name} ready to die error: {response.get_error()}")
        return True

      ready = response.response.body.get("ready", False)
      assumptions = response.response.body.get("assumptions", None)
      why = response.response.body.get("why", None)

      self._logger.debug(
        f"plugin {plugin_name} ready to die: {ready} (why={why}, assumptions={assumptions})"
      )

      return bool(ready)

    except Exception as e:
      self._logger.warning(f"{plugin_name}.is_ready_to_die error: {e}")
      return True


class ShutdownControllerImpl(ShutdownController):
  _plugin: PowerPlugin

  def __init__(
    self, plugin: PowerPlugin, shutdown_logic: ShutdownLogic, previous_config: ShutdownConfig
  ):
    super().__init__(
      plugin.runner.videoreg, plugin.runner.power_supply, plugin.logger, shutdown_logic, previous_config
    )
    self._plugin = plugin

  def get_wakeup_config(self):
    return self._plugin.state.get(const.STATE_KEY_WAKEUP)

  async def _log_shutdown(self, shutdown_config):
    bat_level = await self._plugin.runner.power_supply.get_battery_percent()
    bat_str = str(bat_level) if bat_level is not None else "unknown"
    if isinstance(self._plugin.runner.power_supply, PiSugar):
      alarm_wakeup_time = await self._plugin.runner.power_supply.get_alarm_wakeup_time()
    else:
      alarm_wakeup_time = "n/a"
    shutdown_config_json_str = json.dumps(shutdown_config.to_json(), indent=2)
    self._logger.warning(f"""Will shutdown:
shutdown_config={shutdown_config_json_str}
bat_level={bat_str}
alarm_wakeup_time={alarm_wakeup_time}
uptime={self._plugin.get_uptime()}""")


# Keep old names as aliases for backward compatibility
PisugarShutdownControllerImpl = ShutdownControllerImpl
