from argparse import Namespace

from plugins.org_vrg_http.plugin import HttpPlugin
from sdk.service import ServiceRunner


async def build_plugin(runner: ServiceRunner, args: Namespace, plugin_manifest: dict) -> HttpPlugin:
  id = plugin_manifest.get("id")
  name = plugin_manifest.get("name")

  plugin = HttpPlugin(id, name, runner)
  plugin.init_logger(args.log_level)

  plugin.init_socket(client_id=name, channels=[], socket_path=None)

  plugin.init_api_client()

  return plugin
