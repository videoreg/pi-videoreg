import asyncio

from plugins.org_vrg_bot.main import Bot, BotChat, Callback
from plugins.org_vrg_bot.telegram_api import TelegramApi
from sdk.socket.api import ApiClient, ApiResponse


class CommandCallback(Callback):
  _api_client: ApiClient
  _tg_api: TelegramApi

  def __init__(self, prefix, api_client: ApiClient, tg_api: TelegramApi):
    super().__init__(prefix)
    self._api_client = api_client
    self._tg_api = tg_api

  async def invoke(self, bot: Bot, chat: BotChat, callback_data: str):
    try:
      parts = callback_data.split("__")
      if len(parts) < 3:
        await self._tg_api.send_message("Error callback_data format!")
        return

      plugin_name = parts[1]
      command_name = parts[2]
      command_args = parts[3] if len(parts) > 3 else None

      api_args = {
        "command": command_name,
        "payload": {"chat_id": chat.chat_id},
        "args": command_args,
        "interface": "bot",
      }

      response: ApiResponse = await self._api_client.exec(f"{plugin_name}.command", args=api_args)

    except Exception as e:
      bot.context.logger.error(e)
      await self._tg_api.send_message("Error!")

    except asyncio.CancelledError:
      bot.context.logger.warning("Callback cancelled")

    except Exception as e:
      bot.context.logger.error(f"Callback exception {type(e).__name__}: {e}")
