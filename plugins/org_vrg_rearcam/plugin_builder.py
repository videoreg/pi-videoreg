from argparse import Namespace

from plugins.org_vrg_rearcam.methods.forget import MethodForget
from plugins.org_vrg_rearcam.methods.get_config import MethodGetConfig
from plugins.org_vrg_rearcam.methods.get_menu_commands import MethodGetMenuCommands
from plugins.org_vrg_rearcam.methods.get_photo import MethodGetPhoto
from plugins.org_vrg_rearcam.methods.get_status import MethodGetStatus
from plugins.org_vrg_rearcam.methods.list_devices import MethodListDevices
from plugins.org_vrg_rearcam.methods.provision import MethodProvision
from plugins.org_vrg_rearcam.methods.scan_ble import MethodScanBle
from plugins.org_vrg_rearcam.methods.set_config import MethodSetConfig
from plugins.org_vrg_rearcam.plugin import RearcamPlugin
from sdk.gateway import Gateway, GatewayCommandMethod
from sdk.service import ServiceRunner


async def build_plugin(
  runner: ServiceRunner, args: Namespace, plugin_manifest: dict
) -> RearcamPlugin:
  id = plugin_manifest.get("id")
  name = plugin_manifest.get("name")

  plugin = RearcamPlugin(id, name, runner)
  plugin.init_logger(args.log_level)
  plugin.init_socket(client_id=name, channels=[name], socket_path=None)
  plugin.init_api_client()

  gateways = Gateway.parse_gateways(
    runner.videoreg.manifest.gateways, plugin.logger, plugin.api_client
  )

  plugin.init_api_servier(
    methods={
      # The commands dict lives on the plugin: /photo_N handlers are added and
      # removed as cameras are paired and forgotten (sync_gateway_commands).
      "command": GatewayCommandMethod(gateways, plugin.gateway_commands),
      "list_devices": MethodListDevices(plugin),
      "scan_ble": MethodScanBle(plugin),
      "provision": MethodProvision(plugin),
      "forget": MethodForget(plugin),
      "get_photo": MethodGetPhoto(plugin),
      "get_status": MethodGetStatus(plugin),
      "get_config": MethodGetConfig(plugin),
      "set_config": MethodSetConfig(plugin),
      "get_menu_commands": MethodGetMenuCommands(plugin),
    }
  )

  plugin.sync_gateway_commands()

  return plugin
