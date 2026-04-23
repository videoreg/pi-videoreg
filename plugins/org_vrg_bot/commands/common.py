import asyncio
from typing import Any

from plugins.org_vrg_bot.main import Bot, BotChat, Command
from plugins.org_vrg_bot.telegram_api import TelegramApi
from sdk.socket.api import ApiClient, ApiResponse


class CommandCommon(Command):
  _api_client: ApiClient
  _tg_api: TelegramApi
  _command: str
  _plugin_name: str

  def __init__(
    self,
    name: str,
    plugin_name: str,
    default_args: Any,
    api_client: ApiClient,
    tg_api: TelegramApi,
  ):
    super().__init__(name)
    self._plugin_name = plugin_name
    self._default_args = default_args
    self._api_client = api_client
    self._tg_api = tg_api

  async def invoke(self, bot: Bot, chat: BotChat, args: str):
    try:
      api_args = {
        "command": self.name,
        "payload": {"chat_id": chat.chat_id},
        "args": args if args else self._default_args,
        "interface": "bot",
      }

      response: ApiResponse = await self._api_client.exec(
        f"{self._plugin_name}.command", args=api_args
      )

    except asyncio.CancelledError:
      bot.context.logger.warning("Common command cancelled")

    except Exception as e:
      bot.context.logger.error(f"Common command error: {e}")
      await self._tg_api.send_message("Error!")
