from argparse import Namespace

from plugins.org_vrg_core.methods.get_journal_files import MethodGetJournalFiles
from plugins.org_vrg_core.methods.get_trip_state import MethodGetTripState
from plugins.org_vrg_core.methods.get_system import MethodGetSystem
from plugins.org_vrg_core.methods.service_action import MethodServiceAction
from plugins.org_vrg_core.methods.set_plugin_enabled import MethodSetPluginEnabled
from plugins.org_vrg_core.plugin import CorePlugin
from sdk.journal import JournalRecord
from sdk.service import ConnectionListenerFactory, PluginConnectionListener, ServiceRunner


class CoreServiceConnectionListener(PluginConnectionListener):
  plugin: CorePlugin

  async def on_data(self, data, to, from_=None):
    if to == "journal":
      try:
        record = JournalRecord.parse(data)
        plugin_id = data.get("from") or from_ or "unknown"
        self.plugin.journal_server.write(plugin_id, record)
      except Exception as e:
        self.plugin.logger.warning(f"journal write error {type(e).__name__}: {e}")


class CoreServiceConnectionListenerFactory(ConnectionListenerFactory):
  def create(self, plugin):
    return CoreServiceConnectionListener(plugin)


async def build_plugin(runner: ServiceRunner, args: Namespace, plugin_manifest: dict) -> CorePlugin:
  id = plugin_manifest.get("id")
  name = plugin_manifest.get("name")

  plugin = CorePlugin(id, name, runner)
  plugin.init_logger(args.log_level)
  plugin.init_socket(
    client_id=name,
    channels=["journal"],
    socket_path=None,
    connection_listener_factory=CoreServiceConnectionListenerFactory(),
  )
  plugin.init_journal_server()
  plugin.init_api_client()
  plugin.init_api_servier(
    methods={
      "get_system": MethodGetSystem(plugin),
      "set_plugin_enabled": MethodSetPluginEnabled(plugin),
      "service_action": MethodServiceAction(plugin),
      "get_journal_files": MethodGetJournalFiles(plugin),
      "get_trip_state": MethodGetTripState(plugin),
    }
  )

  return plugin
