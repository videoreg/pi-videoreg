from argparse import Namespace

from plugins.org_vrg_stat.commands.get_commands import CommandGetCommands
from plugins.org_vrg_stat.commands.get_temp import CommandGetTemp
from plugins.org_vrg_stat.dirs import Dirs
from plugins.org_vrg_stat.methods.get_current_temp import MethodGetCurrentTemp
from plugins.org_vrg_stat.methods.get_pisugar_history import MethodGetPisugarHistory
from plugins.org_vrg_stat.methods.get_temp_history import MethodGetTempHistory
from plugins.org_vrg_stat.methods.get_traffic_hourly_history import MethodGetTrafficHourlyHistory
from plugins.org_vrg_stat.methods.storage_info import MethodStorageInfo
from plugins.org_vrg_stat.plugin import StatPlugin
from sdk.interface import Interface, InterfaceCommand, InterfaceCommandMethod
from sdk.service import ServiceRunner


async def build_plugin(runner: ServiceRunner, args: Namespace, plugin_manifest: dict) -> StatPlugin:
  id = plugin_manifest.get("id")
  name = plugin_manifest.get("name")

  plugin = StatPlugin(id, name, runner)
  plugin.init_logger(args.log_level)
  plugin.init_socket(client_id=name, channels=[], socket_path=None)
  plugin.init_api_client()

  dirs = Dirs(runner.videoreg, plugin_id=id)

  if args.env == "dev":
    from plugins.org_vrg_stat.dev.tracker import TrackerImpl

    tracker = TrackerImpl()
  else:
    from plugins.org_vrg_stat.prod.tracker import TrackerImpl

    tracker = TrackerImpl(plugin.logger, runner.power_supply, dirs)

  plugin.init_tracker(tracker)

  interfaces = Interface.parse_interfaces(
    runner.videoreg.manifest.interfaces, plugin.logger, plugin.api_client
  )
  commands: dict[str, InterfaceCommand] = {
    "stat": CommandGetCommands(),
    "temp": CommandGetTemp(),
  }

  plugin.init_api_servier(
    methods={
      "command": InterfaceCommandMethod(interfaces, commands),
      # "get_commands": MethodGetCommands(),
      "storage_info": MethodStorageInfo(),
      "get_current_temp": MethodGetCurrentTemp(),
      "get_temp_history": MethodGetTempHistory(dirs),
      "get_pisugar_history": MethodGetPisugarHistory(dirs),
      "get_traffic_hourly_history": MethodGetTrafficHourlyHistory(dirs),
    }
  )

  return plugin
