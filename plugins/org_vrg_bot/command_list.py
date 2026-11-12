"""Building the bot's command list.

Static commands come from the merged manifest (see `read_menu_commands`);
dynamic ones (e.g. rearcam's `/photo_N`, one per paired camera) are pulled at
runtime from every plugin declaring `bot.menu_commands_method` in its manifest
(see `sdk.gateway_menu.read_menu_commands_methods`). Used by the plugin builder
at startup and by `bot.reload_commands` when a plugin's dynamic set changes.
"""

from logging import Logger

from plugins.org_vrg_bot.commands.api import CommandApi
from plugins.org_vrg_bot.commands.common import CommandCommon
from plugins.org_vrg_bot.commands.start import CommandStart
from plugins.org_vrg_bot.main import BotCommand, Command
from plugins.org_vrg_bot.plugin import BotPlugin
from plugins.org_vrg_bot.telegram_api import TelegramApi
from sdk.gateway_menu import read_menu_commands, read_menu_commands_methods
from sdk.socket.api import ApiClient


async def fetch_dynamic_menu_commands(
  api_client: ApiClient, merged_plugins: list[dict], logger: Logger
) -> list[dict]:
  """Query every plugin's `bot.menu_commands_method` for extra menu commands."""
  commands: list[dict] = []
  for plugin_name, method in read_menu_commands_methods(merged_plugins):
    try:
      response = await api_client.exec(method, args=None, timeout=10)
    except Exception as e:
      logger.warning(f"{method} failed: {e}; skipping its dynamic menu commands")
      continue
    if not response.is_ok():
      logger.warning(f"{method} returned {response.get_error()}; skipping")
      continue
    data = response.get_data() or {}
    for cmd in data.get("commands", []) or []:
      if isinstance(cmd, dict) and cmd.get("name") and cmd.get("title"):
        commands.append({**cmd, "plugin": plugin_name})
  return commands


def build_command_list(
  plugin: BotPlugin,
  merged_plugins: list[dict],
  gateway_name: str,
  tg_api: TelegramApi,
  dynamic_commands: list[dict] = None,
) -> tuple[list[Command], list[BotCommand]]:
  """Assemble the dispatcher command list and the Telegram menu entries.

  Returns (commands, bot_commands): the dispatcher handlers (`/start`, `/api`
  plus one CommandCommon per menu command) and the `BotCommand` entries pushed
  to Telegram via setMyCommands.
  """
  menu_commands = read_menu_commands(merged_plugins, gateway_name)
  menu_commands.extend(dynamic_commands or [])
  menu_commands.sort(key=lambda c: (-(c.get("weigh") or 0), c.get("name") or ""))

  bot_commands: list[BotCommand] = []
  common_commands: list[CommandCommon] = []

  for manifest_command in menu_commands:
    name = manifest_command.get("name")
    title = manifest_command.get("title")
    hidden = manifest_command.get("hidden", False)
    default_args = manifest_command.get("args", None)
    plugin_name = manifest_command.get("plugin")

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

  commands: list[Command] = [
    CommandStart(plugin=plugin, tg_api=tg_api, name="start", commands=bot_commands),
    CommandApi(name="api", plugin=plugin, api_client=plugin.api_client, tg_api=tg_api),
    *common_commands,
  ]
  return commands, bot_commands
