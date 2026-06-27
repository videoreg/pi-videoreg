from argparse import Namespace

from plugins.org_vrg_sms.commands.get_commands import CommandGetCommands
from plugins.org_vrg_sms.commands.get_sms import CommandGetSms
from plugins.org_vrg_sms.commands.list_sms import CommandListSms
from plugins.org_vrg_sms.methods.delete_sms import MethodDeleteSms
from plugins.org_vrg_sms.methods.get_all_sms import MethodGetAllSms
from plugins.org_vrg_sms.methods.is_ready_to_die import MethodIsReadyToDie
from plugins.org_vrg_sms.methods.send_text import MethodSendText
from plugins.org_vrg_sms.plugin import SmsPlugin
from sdk.command_reader import read_plugin_commands
from sdk.gateway import Gateway, GatewayCommand, GatewayCommandMethod
from sdk.service import ServiceRunner
from sdk.user_manager import UserManager


async def build_plugin(runner: ServiceRunner, args: Namespace, plugin_manifest: dict) -> SmsPlugin:
  id = plugin_manifest.get("id")
  name = plugin_manifest.get("name")

  plugin = SmsPlugin(id, name, runner)
  plugin.init_logger(args.log_level)
  plugin.init_socket(client_id=name, channels=[], socket_path=None)

  if args.env == "dev":
    from plugins.org_vrg_sms.dev.sms_manager import SmsManagerImpl

    sms_manager = SmsManagerImpl()
  else:
    from plugins.org_vrg_sms.prod.sms_manager import SmsManagerImpl

    sms_manager = SmsManagerImpl(plugin.logger)

  plugin.init_sms_manager(sms_manager)
  plugin.init_api_client()

  gateways = Gateway.parse_gateways(
    runner.videoreg.manifest.gateways, plugin.logger, plugin.api_client
  )
  commands: dict[str, GatewayCommand] = {
    "sms": CommandGetCommands(plugin),
    "list_sms": CommandListSms(plugin),
    "get_sms": CommandGetSms(plugin),
  }

  plugin.init_api_servier(
    methods={
      "command": GatewayCommandMethod(gateways, commands),
      "is_ready_to_die": MethodIsReadyToDie(plugin),
      "send_text": MethodSendText(plugin),
      "get_all_sms": MethodGetAllSms(plugin),
      "delete_sms": MethodDeleteSms(plugin),
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
