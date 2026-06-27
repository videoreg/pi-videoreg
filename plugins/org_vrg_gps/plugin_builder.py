from argparse import Namespace

from plugins.org_vrg_gps.commands.get_commands import CommandGetCommands
from plugins.org_vrg_gps.commands.list_tracks import CommandListTracks
from plugins.org_vrg_gps.commands.send_track import CommandSendTrack
from plugins.org_vrg_gps.methods.delete_track import MethodDeleteTrack
from plugins.org_vrg_gps.methods.get_location import MethodGetLocation
from plugins.org_vrg_gps.methods.get_tracks import MethodGetTracks
from plugins.org_vrg_gps.plugin import GpsPlugin
from sdk.gateway import Gateway, GatewayCommand, GatewayCommandMethod
from sdk.service import ServiceRunner


async def build_plugin(runner: ServiceRunner, args: Namespace, plugin_manifest: dict) -> GpsPlugin:
  id = plugin_manifest.get("id")
  name = plugin_manifest.get("name")

  plugin = GpsPlugin(id, name, runner)
  plugin.init_logger(args.log_level)
  plugin.init_socket(client_id=name, channels=[], socket_path=None)

  if args.env == "prod":
    from plugins.org_vrg_gps.prod.modem import ModemImpl
    from sdk.at.transport import DEFAULT_MODEM_DEVICE, shared_transport

    # Shared with the SMS plugin in the same vrg-modem process (one serial port).
    device = plugin_manifest.get("modem_device") or DEFAULT_MODEM_DEVICE
    transport = shared_transport(runner, device, logger=plugin.logger)
    modem = ModemImpl(plugin.logger, transport)
  else:
    from plugins.org_vrg_gps.dev.modem import ModemImpl

    modem = ModemImpl()

  plugin.init_modem(modem)
  plugin.init_journal_client()
  plugin.init_api_client()

  gateways = Gateway.parse_gateways(
    runner.videoreg.manifest.gateways, plugin.logger, plugin.api_client
  )
  commands: dict[str, GatewayCommand] = {
    "gps": CommandGetCommands(plugin),
    "list_tracks": CommandListTracks(plugin),
    "send_track": CommandSendTrack(plugin),
  }

  plugin.init_api_servier(
    methods={
      "command": GatewayCommandMethod(gateways, commands),
      # "get_commands": MethodGetCommands(plugin),
      "get_location": MethodGetLocation(plugin),
      "get_tracks": MethodGetTracks(plugin),
      "delete_track": MethodDeleteTrack(plugin),
    }
  )

  return plugin
