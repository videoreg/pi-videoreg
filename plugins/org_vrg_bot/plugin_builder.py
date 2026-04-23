import asyncio
from argparse import ArgumentParser, Namespace

import sdk.log as log
from plugins.org_vrg_bot.callbacks.command_callback import CommandCallback
from plugins.org_vrg_bot.commands.api import CommandApi
from plugins.org_vrg_bot.commands.common import CommandCommon
from plugins.org_vrg_bot.commands.start import CommandStart
from plugins.org_vrg_bot.dispatcher import Dispatcher
from plugins.org_vrg_bot.main import Bot, BotChat, BotCommand, Context
from plugins.org_vrg_bot.methods.get_settings import MethodGetSettings
from plugins.org_vrg_bot.methods.is_ready_to_die import MethodIsReadyToDie
from plugins.org_vrg_bot.methods.send_document import MethodSendDocument
from plugins.org_vrg_bot.methods.send_image import MethodSendImage
from plugins.org_vrg_bot.methods.send_status import MethodSendStatus
from plugins.org_vrg_bot.methods.send_text import MethodSendText
from plugins.org_vrg_bot.methods.send_video import MethodSendVideo
from plugins.org_vrg_bot.methods.set_settings import MethodSetSettings
from plugins.org_vrg_bot.plugin import BotPlugin
from plugins.org_vrg_bot.telegram_api import TelegramApi
from sdk.service import ConnectionListenerFactory, ServiceRunner
from sdk.user_manager import UserManager


async def build_plugin(runner: ServiceRunner, args: Namespace, plugin_manifest: dict) -> BotPlugin:
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

  plugin = BotPlugin(id, name, runner)
  plugin.init_logger(args.log_level)

  # Wait in a loop until the bot token appears.
  users_file_path = runner.videoreg.private_path("data/users.json")
  TOKEN = None
  while not TOKEN:
    plugin.state.reload()
    TOKEN = plugin.state.get("tg_bot_token")
    if not TOKEN:
      print("Waiting for bot settings (tg_bot_token not set). Retrying in 5 seconds...")
      await asyncio.sleep(5)

  user_manager = UserManager(users_file_path)
  all_users = user_manager.get_all_users()
  chats = [
    BotChat(u["username"], u["plugin_fields"]["org_vrg_bot"]["tg_user_id"])
    for u in all_users
    if u.get("plugin_fields", {}).get("org_vrg_bot", {}).get("tg_user_id")
  ]
  plugin.init_socket(
    client_id=name,
    channels=["notify", "event"],
    socket_path=None,
    connection_listener_factory=ConnectionListenerFactory(),
  )
  plugin.init_api_client()

  http_log_file_path = runner.videoreg.private_path("log/bot_http.log")
  http_rotating_file_handler = log.create_rotating_file_handler(http_log_file_path, tag="bot_http:")
  http_logger = log.create_logger(
    "http_logger", args.http_log_level, http_rotating_file_handler, tag="bot_http:"
  )

  context = Context(state=plugin.state, logger=plugin.logger, http_logger=http_logger)

  bot = Bot(TOKEN, chats, context)

  tg_api = TelegramApi(bot, http_logger)

  plugin.init_api_servier(
    methods={
      "send_video": MethodSendVideo(plugin, bot, tg_api),
      "send_image": MethodSendImage(plugin, bot, tg_api),
      "send_text": MethodSendText(plugin, bot, tg_api),
      "send_document": MethodSendDocument(plugin, bot, tg_api),
      "send_status": MethodSendStatus(plugin, bot, tg_api),
      "is_ready_to_die": MethodIsReadyToDie(plugin),
      "get_settings": MethodGetSettings(plugin),
      "set_settings": MethodSetSettings(plugin, tg_api),
    }
  )

  bot_commands: list[BotCommand] = []
  common_commands: list[CommandCommon] = []

  for plugin_manifest in runner.videoreg.manifest.plugins:
    plugin_name = plugin_manifest.get("name")
    for manifest_command in plugin_manifest.get("commands", []):
      name = manifest_command.get("name")
      title = manifest_command.get("title")
      hidden = manifest_command.get("hidden", False)
      default_args = manifest_command.get("args", None)

      if not name or not title:
        plugin.logger.error(f"yaml wrong command format ({name}, {title}): {manifest_command}")
        continue

      if not hidden:
        bot_commands.append(BotCommand(f"/{name}", title))

      common_commands.append(
        CommandCommon(
          name=name,
          plugin_name=plugin_name,
          default_args=default_args,
          api_client=plugin.api_client,
          tg_api=tg_api,
        )
      )

  commands = [
    CommandStart(plugin=plugin, tg_api=tg_api, name="start", commands=bot_commands),
    CommandApi(name="api", plugin=plugin, api_client=plugin.api_client, tg_api=tg_api),
    *common_commands,
  ]

  callbacks = [
    CommandCallback(prefix="command__", api_client=plugin.api_client, tg_api=tg_api),
  ]

  plugin.dispatcher = Dispatcher(bot, tg_api, commands, callbacks, plugin.keep_alive)
  plugin.tg_api = tg_api

  return plugin
