import asyncio
import json

from plugins.org_vrg_botvk.keyboard import inline_callback_keyboard
from plugins.org_vrg_botvk.main import Bot, BotChat, Command
from plugins.org_vrg_botvk.plugin import BotvkPlugin
from plugins.org_vrg_botvk.vk_api import VkApi
from sdk.socket.api import ApiClient, ApiResponse
from sdk.socket.requests import RequestTimeoutError


class CommandApi(Command):
  _plugin: BotvkPlugin
  _api_client: ApiClient
  _vk_api: VkApi

  def __init__(self, name: str, plugin: BotvkPlugin, api_client: ApiClient, vk_api: VkApi):
    super().__init__(name)
    self._plugin = plugin
    self._api_client = api_client
    self._vk_api = vk_api

  async def invoke(self, bot: Bot, chat: BotChat, args: str):
    method_name = None
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
      except Exception:
        raise Exception("wrong arguments json format")

      response: ApiResponse = await self._api_client.exec(method_name, method_args)

      if not isinstance(response.response.body, dict):
        await self._vk_api.send_message(chat.chat_id, "Bad response!")
        return

      status = response.response.body.get("status", None)

      if status != "ok":
        await self._vk_api.send_message(chat.chat_id, f'Error: response status "{status}"')
        return

      message_text = "Result"
      keyboard = None

      if "bot_message" in response.response.body:
        message_text = response.response.body.get("bot_message", None)

      if "bot_buttons" in response.response.body:
        keyboard = inline_callback_keyboard(response.response.body.get("bot_buttons", None))

      if message_text or keyboard:
        await self._vk_api.send_message(chat.chat_id, message_text, keyboard=keyboard)
      else:
        await self._vk_api.send_message(
          chat.chat_id, json.dumps(response.response.body, indent=2)
        )

    except RequestTimeoutError:
      await self._vk_api.send_message(chat.chat_id, f"API {method_name} timeout")

    except asyncio.CancelledError:
      self._plugin.logger.debug("command api cancelled")

    except Exception as e:
      await self._vk_api.send_message(chat.chat_id, f"API error: {e}")
