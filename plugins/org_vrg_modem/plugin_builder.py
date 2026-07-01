from argparse import Namespace

from plugins.org_vrg_modem.commands.get_sms import CommandGetSms
from plugins.org_vrg_modem.commands.gps_commands import CommandGpsCommands
from plugins.org_vrg_modem.commands.list_sms import CommandListSms
from plugins.org_vrg_modem.commands.list_tracks import CommandListTracks
from plugins.org_vrg_modem.commands.send_track import CommandSendTrack
from plugins.org_vrg_modem.commands.sms_commands import CommandSmsCommands
from plugins.org_vrg_modem.methods.delete_sms import MethodDeleteSms
from plugins.org_vrg_modem.methods.delete_track import MethodDeleteTrack
from plugins.org_vrg_modem.methods.get_all_sms import MethodGetAllSms
from plugins.org_vrg_modem.methods.get_apn import MethodGetApn
from plugins.org_vrg_modem.methods.get_location import MethodGetLocation
from plugins.org_vrg_modem.methods.get_modem_info import MethodGetModemInfo
from plugins.org_vrg_modem.methods.get_tracks import MethodGetTracks
from plugins.org_vrg_modem.methods.is_ready_to_die import MethodIsReadyToDie
from plugins.org_vrg_modem.methods.send_text import MethodSendText
from plugins.org_vrg_modem.methods.set_apn import MethodSetApn
from plugins.org_vrg_modem.plugin import ModemPlugin
from sdk.command_reader import read_plugin_commands
from sdk.gateway import Gateway, GatewayCommand, GatewayCommandMethod
from sdk.service import ServiceRunner
from sdk.user_manager import UserManager


async def build_plugin(runner: ServiceRunner, args: Namespace, plugin_manifest: dict) -> ModemPlugin:
  id = plugin_manifest.get("id")
  name = plugin_manifest.get("name")

  plugin = ModemPlugin(id, name, runner)
  plugin.init_logger(args.log_level)
  plugin.init_socket(client_id=name, channels=[], socket_path=None)

  if args.env == "prod":
    from plugins.org_vrg_modem.prod.modem import ModemImpl
    from plugins.org_vrg_modem.prod.sms_manager import SmsManagerImpl
    from sdk.at.transport import DEFAULT_MODEM_DEVICE, shared_transport

    # GPS and SMS share one serial port (this plugin owns it): a single
    # AtTransport opens the port once and serialises access via its lock.
    device = plugin_manifest.get("modem_device") or DEFAULT_MODEM_DEVICE
    transport = shared_transport(runner, device, logger=plugin.logger)
    modem = ModemImpl(plugin.logger, transport)
    sms_manager = SmsManagerImpl(plugin.logger, transport)
  else:
    from plugins.org_vrg_modem.dev.modem import ModemImpl
    from plugins.org_vrg_modem.dev.sms_manager import SmsManagerImpl

    modem = ModemImpl()
    sms_manager = SmsManagerImpl()

  plugin.init_modem(modem)
  plugin.init_sms_manager(sms_manager)
  plugin.init_journal_client()
  plugin.init_api_client()

  gateways = Gateway.parse_gateways(
    runner.videoreg.manifest.gateways, plugin.logger, plugin.api_client
  )
  commands: dict[str, GatewayCommand] = {
    "gps": CommandGpsCommands(plugin),
    "list_tracks": CommandListTracks(plugin),
    "send_track": CommandSendTrack(plugin),
    "sms": CommandSmsCommands(plugin),
    "list_sms": CommandListSms(plugin),
    "get_sms": CommandGetSms(plugin),
  }

  plugin.init_api_servier(
    methods={
      "command": GatewayCommandMethod(gateways, commands),
      "get_location": MethodGetLocation(plugin),
      "get_tracks": MethodGetTracks(plugin),
      "delete_track": MethodDeleteTrack(plugin),
      "is_ready_to_die": MethodIsReadyToDie(plugin),
      "send_text": MethodSendText(plugin),
      "get_all_sms": MethodGetAllSms(plugin),
      "delete_sms": MethodDeleteSms(plugin),
      "modem_info": MethodGetModemInfo(plugin),
      "get_apn": MethodGetApn(plugin),
      "set_apn": MethodSetApn(plugin),
    }
  )

  # Commands are declared in each plugin's manifest.yaml (read by read_plugin_commands).
  plugins_dir = runner.videoreg.app_path("plugins")
  command_plugin_map: dict[str, str] = {}
  for cmd in read_plugin_commands(plugins_dir, runner.videoreg.manifest.plugins):
    cmd_name = cmd.get("name")
    if cmd_name:
      command_plugin_map[cmd_name] = cmd.get("plugin")

  plugin.init_command_plugin_map(command_plugin_map)

  users_file_path = runner.videoreg.private_path("data/users.json")
  user_manager = UserManager(users_file_path)
  allowed_phones = [
    u["plugin_fields"]["org_vrg_sms"]["phone"]
    for u in user_manager.get_all_users()
    if u.get("plugin_fields", {}).get("org_vrg_sms", {}).get("phone")
  ]
  plugin.init_allowed_phones(allowed_phones)

  return plugin
