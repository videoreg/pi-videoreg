import asyncio

from plugins.org_vrg_bot.main import Bot, BotChat, BotCommand, Command
from plugins.org_vrg_bot.plugin import BotPlugin
from plugins.org_vrg_bot.telegram_api import TelegramApi


class CommandStart(Command):
  _plugin: BotPlugin
  _commands: list[BotCommand]
  _tg_api: TelegramApi

  def __init__(self, plugin: BotPlugin, tg_api: TelegramApi, name, commands: list[BotCommand]):
    super().__init__(name)
    self._plugin = plugin
    self._commands = commands
    self._tg_api = tg_api

  async def invoke(self, bot: Bot, chat: BotChat, args: str):
    try:
      name = self._plugin.state.get("tg_bot_name", "Videoreg")
      await self._tg_api.set_my_name(name)
      await self._tg_api.set_my_commands(chat.chat_id, self._commands)
      await self._tg_api.send_message(chat.chat_id, "Welcome to videoreg!")

    except asyncio.CancelledError:
      self._plugin.logger.warning("command start cancelled")

    except Exception as e:
      self._plugin.logger.error(f"command start exception {type(e).__name__}: {e}")
