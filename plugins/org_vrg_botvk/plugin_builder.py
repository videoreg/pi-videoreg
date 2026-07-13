from argparse import ArgumentParser, Namespace

import sdk.log as log
from plugins.org_vrg_botvk.callbacks.command_callback import CommandCallback
from plugins.org_vrg_botvk.callbacks.command_edit_callback import CommandEditCallback
from plugins.org_vrg_botvk.commands.api import CommandApi
from plugins.org_vrg_botvk.commands.common import CommandCommon
from plugins.org_vrg_botvk.commands.start import CommandStart
from plugins.org_vrg_botvk.dispatcher import Dispatcher
from plugins.org_vrg_botvk.main import Bot, BotChat, Context, MenuButton
from plugins.org_vrg_botvk.methods.edit_message import MethodEditMessage
from plugins.org_vrg_botvk.methods.get_settings import MethodGetSettings
from plugins.org_vrg_botvk.methods.get_status import MethodGetStatus
from plugins.org_vrg_botvk.methods.is_ready_to_die import MethodIsReadyToDie
from plugins.org_vrg_botvk.methods.send_document import MethodSendDocument
from plugins.org_vrg_botvk.methods.send_image import MethodSendImage
from plugins.org_vrg_botvk.methods.send_status import MethodSendStatus
from plugins.org_vrg_botvk.methods.send_text import MethodSendText
from plugins.org_vrg_botvk.methods.set_settings import MethodSetSettings
from plugins.org_vrg_botvk.plugin import BotvkPlugin
from plugins.org_vrg_botvk.vk_api import VkApi
from sdk.gateway import Gateway, GatewayCommandMethod
from sdk.gateway_menu import build_menu_gateway_commands, read_menu_commands
from sdk.service import ConnectionListenerFactory, ServiceRunner
from sdk.user_manager import UserManager


async def build_plugin(runner: ServiceRunner, args: Namespace, plugin_manifest: dict) -> BotvkPlugin:
  parser = ArgumentParser()
  parser.add_argument(
    "--http-log-level",
    dest="http_log_level",
    type=str,
    help="Log level of HTTP requests: DEBUG,INFO,WARNING,ERROR",
    default="WARNING",
    required=False,
  )
  parser.add_argument(
    "--log-level",
    dest="log_level",
    type=str,
    help="Log level: DEBUG,INFO,WARNING,ERROR",
    default="WARNING",
    required=False,
  )

  args, unknown = parser.parse_known_args()

  id = plugin_manifest.get("id")
  name = plugin_manifest.get("name")

  plugin = BotvkPlugin(id, name, runner)
  plugin.init_logger(args.log_level)

  # Token / group id may be empty at startup; BotvkPlugin.start() waits for them
  # before starting the dispatcher. The plugin still initializes so videoreg-api
  # methods (e.g. botvk.set_settings) are reachable to set the credentials.
  users_file_path = runner.videoreg.private_path("data/users.json")
  TOKEN = plugin.state.get("vk_bot_token", "")
  GROUP_ID = plugin.state.get("vk_group_id", "")

  user_manager = UserManager(users_file_path)

  def load_chats() -> list[BotChat]:
    user_manager.reload()
    return [
      BotChat(u["username"], u["plugin_fields"]["org_vrg_botvk"]["vk_user_id"])
      for u in user_manager.get_all_users()
      if u.get("plugin_fields", {}).get("org_vrg_botvk", {}).get("vk_user_id")
    ]

  plugin.init_socket(
    client_id=name,
    channels=["notify", "event"],
    socket_path=None,
    connection_listener_factory=ConnectionListenerFactory(),
  )
  plugin.init_api_client()

  http_log_file_path = runner.videoreg.private_path("log/botvk_http.log")
  http_rotating_file_handler = log.create_rotating_file_handler(
    http_log_file_path, tag="botvk_http:"
  )
  http_logger = log.create_logger(
    "http_logger", args.http_log_level, http_rotating_file_handler, tag="botvk_http:"
  )

  context = Context(state=plugin.state, logger=plugin.logger, http_logger=http_logger)

  bot = Bot(TOKEN, GROUP_ID, load_chats(), context)

  vk_api = VkApi(bot, http_logger)

  # `/more` and `/status` are shared bot-menu commands handled by this gateway itself
  # (botvk.command) via the standard gateway command flow. The logic lives in the SDK so
  # each bot gateway registers its own copy and stays independent of the others.
  plugins_dir = runner.videoreg.app_path("plugins")
  gateways = Gateway.parse_gateways(
    runner.videoreg.manifest.gateways, plugin.logger, plugin.api_client
  )
  gateway_commands = build_menu_gateway_commands(
    plugin.api_client, plugins_dir, runner.videoreg.manifest.plugins
  )

  plugin.init_api_servier(
    methods={
      "command": GatewayCommandMethod(gateways, gateway_commands),
      "send_image": MethodSendImage(plugin, bot, vk_api),
      "send_text": MethodSendText(plugin, bot, vk_api),
      "edit_message": MethodEditMessage(plugin, bot, vk_api),
      "send_document": MethodSendDocument(plugin, bot, vk_api),
      "send_status": MethodSendStatus(plugin, bot, vk_api),
      "is_ready_to_die": MethodIsReadyToDie(plugin),
      "get_settings": MethodGetSettings(plugin),
      "get_status": MethodGetStatus(plugin),
      "set_settings": MethodSetSettings(plugin),
    }
  )

  menu_buttons: list[MenuButton] = []
  common_commands: list[CommandCommon] = []

  # Commands are declared in each plugin's manifest.yaml (plus the shared /more & /status);
  # read_menu_commands returns them sorted by `weigh` descending, which defines the menu
  # keyboard order. The built-in commands route to this gateway's own botvk.command.
  for manifest_command in read_menu_commands(
    plugins_dir, runner.videoreg.manifest.plugins, plugin_manifest.get("name")
  ):
    cmd_name = manifest_command.get("name")
    title = manifest_command.get("title")
    hidden = manifest_command.get("hidden", False)
    default_args = manifest_command.get("args", None)
    plugin_name = manifest_command.get("plugin")

    if not cmd_name or not title:
      plugin.logger.error(f"yaml wrong command format ({cmd_name}, {title}): {manifest_command}")
      continue

    if not hidden:
      # VK has no native command menu; expose commands as keyboard callback buttons.
      menu_buttons.append(MenuButton(title, f"command__{plugin_name}__{cmd_name}"))

    common_commands.append(
      CommandCommon(
        name=cmd_name,
        plugin_name=plugin_name,
        default_args=default_args,
        api_client=plugin.api_client,
        vk_api=vk_api,
      )
    )

  commands = [
    CommandStart(plugin=plugin, vk_api=vk_api, name="start", menu_buttons=menu_buttons),
    CommandApi(name="api", plugin=plugin, api_client=plugin.api_client, vk_api=vk_api),
    *common_commands,
  ]

  callbacks = [
    CommandCallback(prefix="command__", api_client=plugin.api_client, vk_api=vk_api),
    CommandEditCallback(prefix="command_edit__", api_client=plugin.api_client, vk_api=vk_api),
  ]

  plugin.dispatcher = Dispatcher(
    bot, vk_api, commands, callbacks, plugin.keep_alive, plugin.health
  )
  plugin.vk_api = vk_api
  plugin.bot = bot
  plugin.chats_loader = load_chats

  return plugin
