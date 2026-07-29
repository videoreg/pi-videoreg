from argparse import Namespace

import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.commands.get_commands import CommandGetCommands
from plugins.org_vrg_power.commands.get_wakeup_commands import CommandGetWakeupCommands
from plugins.org_vrg_power.commands.keep_alive import CommandKeepAlive
from plugins.org_vrg_power.commands.no import CommandNo
from plugins.org_vrg_power.commands.reboot import CommandReboot
from plugins.org_vrg_power.commands.set_wakeup import CommandSetWakeup
from plugins.org_vrg_power.commands.shutdown import CommandShutdown
from plugins.org_vrg_power.ble_beacon import BleBeaconMonitor
from plugins.org_vrg_power.methods.ble_scan import MethodBleScan
from plugins.org_vrg_power.methods.clear_ble_target import MethodClearBleTarget
from plugins.org_vrg_power.methods.get_beacon_state import MethodGetBeaconState
from plugins.org_vrg_power.methods.get_ble_config import MethodGetBleConfig
from plugins.org_vrg_power.methods.get_capabilities import MethodGetCapabilities
from plugins.org_vrg_power.methods.get_charging_protection import MethodGetChargingProtection
from plugins.org_vrg_power.methods.set_ble_enabled import MethodSetBleEnabled
from plugins.org_vrg_power.methods.set_ble_grace import MethodSetBleGrace
from plugins.org_vrg_power.methods.set_ble_target import MethodSetBleTarget
from plugins.org_vrg_power.methods.get_status import MethodGetStatus
from plugins.org_vrg_power.methods.get_status_text import MethodGetStatusText
from plugins.org_vrg_power.methods.get_wakeup_config import MethodGetWakeupConfig
from plugins.org_vrg_power.methods.set_charging_protection import MethodSetChargingProtection
from plugins.org_vrg_power.methods.is_ready_to_die import MethodIsReadyToDie
from plugins.org_vrg_power.methods.keep_alive import MethodKeepAlive
from plugins.org_vrg_power.methods.power_status_generic import MethodPowerStatusGeneric
from plugins.org_vrg_power.methods.reboot import MethodReboot
from plugins.org_vrg_power.methods.set_wakeup import MethodSetWakeup
from plugins.org_vrg_power.methods.shutdown import MethodShutdown
from plugins.org_vrg_power.plugin import PowerPlugin
from plugins.org_vrg_power.shutdown import ShutdownController, ShutdownConfig, ShutdownLogic
from sdk.gateway import Gateway, GatewayCommand, GatewayCommandMethod
from sdk.service import ServiceRunner


async def build_plugin(
  runner: ServiceRunner, args: Namespace, plugin_manifest: dict
) -> PowerPlugin:
  id = plugin_manifest.get("id")
  name = plugin_manifest.get("name")

  plugin = PowerPlugin(id, name, runner)
  plugin.init_logger(args.log_level)
  plugin.init_socket(client_id=name, channels=[], socket_path=None)
  plugin.init_api_client()
  plugin.init_journal_client()

  plugin.state.set_defaults(
    defaults={
      const.STATE_KEY_WAKEUP: "on-power-restore",
      const.STATE_KEY_CHARGING_PROTECTION: True,
      const.STATE_KEY_BLE_ENABLED: False,
      const.STATE_KEY_BLE_TARGET: None,
      const.STATE_KEY_BLE_GRACE_MINUTES: const.BLE_GRACE_MINUTES_DEFAULT,
    }
  )

  plugin.init_ble_monitor(BleBeaconMonitor(plugin, plugin.logger))

  previous_shutdown_config = ShutdownConfig.from_json(
    plugin.state.get(const.STATE_KEY_LAST_SHUTDOWN_CONFIG, None)
  )

  if args.env == "dev":
    from plugins.org_vrg_power.dev.shutdown import ShutdownControllerImpl, ShutdownLogicImpl
    from plugins.org_vrg_power.dev.power_controls import PowerControlsImpl

    shutdown_logic = ShutdownLogicImpl()
    shutdown_controller = ShutdownControllerImpl(
      videoreg=runner.videoreg,
      power_supply=runner.power_supply,
      logger=plugin.logger,
      shutdown_logic=shutdown_logic,
      previous_config=previous_shutdown_config,
    )
    power_controls = PowerControlsImpl(plugin.logger)
  else:
    from plugins.org_vrg_power.prod.shutdown import ShutdownControllerImpl, ShutdownLogicImpl
    from plugins.org_vrg_power.prod.power_controls import PowerControlsImpl
    from plugins.org_vrg_power.shutdown_plugins_reader import read_ask_before_shutdown_plugins

    ask_plugins = read_ask_before_shutdown_plugins(
      runner.videoreg.merged_manifest()["plugins"]
    )
    plugin.logger.info(f"Plugins asked before shutdown: {ask_plugins}")

    shutdown_logic = ShutdownLogicImpl(
      plugin.runner.videoreg,
      plugin.logger,
      plugin.runner.power_supply,
      plugin.api_client,
      ask_plugins,
    )
    shutdown_controller = ShutdownControllerImpl(
      plugin=plugin, shutdown_logic=shutdown_logic, previous_config=previous_shutdown_config
    )
    power_controls = PowerControlsImpl(plugin.logger)

  plugin.init_shutdown(shutdown_logic, shutdown_controller)
  plugin.init_power_controls(power_controls)

  gateways = Gateway.parse_gateways(
    runner.videoreg.manifest.gateways, plugin.logger, plugin.api_client
  )
  commands: dict[str, GatewayCommand] = {
    "power": CommandGetCommands(plugin, runner.power_supply),
    "wakeup_commands": CommandGetWakeupCommands(plugin),
    "set_wakeup": CommandSetWakeup(plugin, runner.power_supply),
    "shutdown": CommandShutdown(
      plugin, shutdown_controller, force_wakeup_config="on-power-restore"
    ),
    "reboot": CommandReboot(plugin),
    "keep": CommandKeepAlive(plugin),
    "no": CommandNo(plugin),
  }

  plugin.init_api_servier(
    methods={
      "command": GatewayCommandMethod(gateways, commands),
      "get_status": MethodGetStatus(plugin, runner.power_supply),
      "get_status_text": MethodGetStatusText(plugin, runner.power_supply),
      "get_charging_status": MethodPowerStatusGeneric(runner.power_supply, "get_charging_status"),
      "get_wakeup_config": MethodGetWakeupConfig(plugin),
      "set_wakeup": MethodSetWakeup(plugin, runner.power_supply),
      "get_charging_protection": MethodGetChargingProtection(plugin),
      "set_charging_protection": MethodSetChargingProtection(plugin, runner.power_supply),
      "get_capabilities": MethodGetCapabilities(runner.power_supply),
      "shutdown": MethodShutdown(
        plugin, shutdown_controller, force_wakeup_config="on-power-restore"
      ),
      "reboot": MethodReboot(plugin),
      "keep_alive": MethodKeepAlive(plugin),
      "is_ready_to_die": MethodIsReadyToDie(plugin),
      "get_ble_config": MethodGetBleConfig(plugin),
      "get_beacon_state": MethodGetBeaconState(plugin),
      "set_ble_enabled": MethodSetBleEnabled(plugin),
      "set_ble_target": MethodSetBleTarget(plugin),
      "set_ble_grace": MethodSetBleGrace(plugin),
      "clear_ble_target": MethodClearBleTarget(plugin),
      "ble_scan": MethodBleScan(plugin),
    }
  )

  return plugin
