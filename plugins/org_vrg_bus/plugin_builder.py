from argparse import Namespace

from plugins.org_vrg_bus.plugin import BusPlugin
from sdk.service import ServiceRunner


async def build_plugin(runner: ServiceRunner, args: Namespace, plugin_manifest: dict) -> BusPlugin:
  id = plugin_manifest.get("id")
  name = plugin_manifest.get("name")

  plugin = BusPlugin(id, name, runner)
  # plugin.init_logger(args.log_level)
  plugin.init_logger("INFO")

  return plugin
