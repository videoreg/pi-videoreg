import asyncio
import json

from plugins.org_vrg_bot.main import Bot, BotChat, Command
from plugins.org_vrg_bot.plugin import BotPlugin
from plugins.org_vrg_bot.telegram_api import TelegramApi
from sdk.socket.api import ApiClient, ApiResponse
from sdk.socket.requests import RequestTimeoutError


class CommandApi(Command):
  _plugin: BotPlugin
  _api_client: ApiClient
  _tg_api: TelegramApi

  def __init__(self, name: str, plugin: BotPlugin, api_client: ApiClient, tg_api: TelegramApi):
    super().__init__(name)
    self._plugin = plugin
    self._api_client = api_client
    self._tg_api = tg_api

  async def invoke(self, bot: Bot, chat: BotChat, args: str):
    try:
      args_list = args.split()

      if len(args_list) == 0:
        raise Exception("method name is empty")

      method_name = args_list[0]
      method_args = None

      if not method_name:
        raise Exception("method name is empty")

      try:
        if len(args_list) > 1:
          method_args = json.loads(args_list[1])
      except:
        raise Exception("wrong arguments json format")

      response: ApiResponse = await self._api_client.exec(method_name, method_args)

      if not isinstance(response.response.body, dict):
        await self._tg_api.send_message(chat.chat_id, "Bad response!")
        return

      status = response.response.body.get("status", None)

      if status != "ok":
        await self._tg_api.send_message(chat.chat_id, f'Error: response status "{status}"')
        return

      message_text = "Result"
      reply_markup = None

      if "bot_message" in response.response.body:
        message_text = response.response.body.get("bot_message", None)

      if "bot_buttons" in response.response.body:
        reply_markup = json.dumps(
          {"inline_keyboard": response.response.body.get("bot_buttons", None)}
        )

      if message_text or reply_markup:
        await self._tg_api.send_message(chat.chat_id, message_text, reply_markup=reply_markup)
      else:
        await self._tg_api.send_message(chat.chat_id, json.dumps(response.response.body, indent=2))

    except RequestTimeoutError:
      await self._tg_api.send_message(chat.chat_id, f"API {method_name} timeout")

    except Exception as e:
      await self._tg_api.send_message(chat.chat_id, f"API error: {e}")

    except asyncio.CancelledError:
      self._plugin.logger.warning("command api cancelled")

    except Exception as e:
      self._plugin.logger.error(f"command start exception {type(e).__name__}: {e}")
