from argparse import Namespace

import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.commands.get_commands import CommandGetCommands
from plugins.org_vrg_power.commands.get_wakeup_commands import CommandGetWakeupCommands
from plugins.org_vrg_power.commands.keep_alive import CommandKeepAlive
from plugins.org_vrg_power.commands.reboot import CommandReboot
from plugins.org_vrg_power.commands.set_wakeup import CommandSetWakeup
from plugins.org_vrg_power.commands.shutdown import CommandShutdown
from plugins.org_vrg_power.methods.get_status import MethodGetStatus
from plugins.org_vrg_power.methods.get_wakeup_config import MethodGetWakeupConfig
from plugins.org_vrg_power.methods.is_ready_to_die import MethodIsReadyToDie
from plugins.org_vrg_power.methods.keep_alive import MethodKeepAlive
from plugins.org_vrg_power.methods.pisugar_generic import MethodPisugarGeneric
from plugins.org_vrg_power.methods.reboot import MethodReboot
from plugins.org_vrg_power.methods.set_wakeup import MethodSetWakeup
from plugins.org_vrg_power.methods.shutdown import MethodShutdown
from plugins.org_vrg_power.plugin import PowerPlugin
from plugins.org_vrg_power.shutdown import ShutdownConfig
from sdk.interface import Interface, InterfaceCommand, InterfaceCommandMethod
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

  plugin.state.set_defaults(defaults={const.STATE_KEY_WAKEUP: "on-power-restore"})

  previous_shutdown_config = ShutdownConfig.from_json(
    plugin.state.get(const.STATE_KEY_LAST_SHUTDOWN_CONFIG, None)
  )

  if args.env == "dev":
    from plugins.org_vrg_power.dev.shutdown import PisugarShutdownControllerImpl, ShutdownLogicImpl

    shutdown_logic = ShutdownLogicImpl()
    shutdown_controller = PisugarShutdownControllerImpl(
      videoreg=runner.videoreg,
      pisugar=runner.pisugar,
      logger=plugin.logger,
      shutdown_logic=shutdown_logic,
      previous_config=previous_shutdown_config,
    )
  else:
    from plugins.org_vrg_power.prod.shutdown import PisugarShutdownControllerImpl, ShutdownLogicImpl

    shutdown_logic = ShutdownLogicImpl(
      plugin.runner.videoreg, plugin.logger, plugin.runner.pisugar, plugin.api_client
    )
    shutdown_controller = PisugarShutdownControllerImpl(
      plugin=plugin, shutdown_logic=shutdown_logic, previous_config=previous_shutdown_config
    )

  plugin.init_shutdown(shutdown_logic, shutdown_controller)

  interfaces = Interface.parse_interfaces(
    runner.videoreg.manifest.interfaces, plugin.logger, plugin.api_client
  )
  commands: dict[str, InterfaceCommand] = {
    "power": CommandGetCommands(plugin, runner.pisugar),
    "wakeup_commands": CommandGetWakeupCommands(plugin),
    "set_wakeup": CommandSetWakeup(plugin, runner.pisugar),
    "shutdown": CommandShutdown(
      plugin, shutdown_controller, force_wakeup_config="on-power-restore"
    ),
    "reboot": CommandReboot(plugin),
    "keep": CommandKeepAlive(plugin),
  }

  plugin.init_api_servier(
    methods={
      "command": InterfaceCommandMethod(interfaces, commands),
      # "get_commands": MethodGetCommands(plugin, runner.pisugar),
      "get_status": MethodGetStatus(plugin, runner.pisugar),
      "get_charging_status": MethodPisugarGeneric(runner.pisugar, "get_charging_status"),
      # "get_bat_level": MethodPisugarGeneric(runner.pisugar, "get_bat_level"),
      # "get_temp": MethodPisugarGeneric(runner.pisugar, "get_temp"),
      "get_wakeup_config": MethodGetWakeupConfig(plugin),
      "set_wakeup": MethodSetWakeup(plugin, runner.pisugar),
      "shutdown": MethodShutdown(
        plugin, shutdown_controller, force_wakeup_config="on-power-restore"
      ),
      "reboot": MethodReboot(plugin),
      "keep_alive": MethodKeepAlive(plugin),
      "is_ready_to_die": MethodIsReadyToDie(plugin),
    }
  )

  return plugin
