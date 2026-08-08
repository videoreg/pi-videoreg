import asyncio

from plugins.org_vrg_botvk.main import Bot, BotChat, Callback
from plugins.org_vrg_botvk.vk_api import VkApi
from sdk.socket.api import ApiClient, ApiResponse


class CommandEditCallback(Callback):
  _api_client: ApiClient
  _vk_api: VkApi

  def __init__(self, prefix, api_client: ApiClient, vk_api: VkApi):
    super().__init__(prefix)
    self._api_client = api_client
    self._vk_api = vk_api

  async def invoke(self, bot: Bot, chat: BotChat, callback_data: str, message_id: int = None):
    try:
      parts = callback_data.split("__")
      if len(parts) < 3:
        await self._vk_api.send_message(chat.chat_id, "Error callback_data format!")
        return

      plugin_name = parts[1]
      command_name = parts[2]
      command_args = parts[3] if len(parts) > 3 else None

      # message_id is the VK conversation_message_id, used by messages.edit.
      api_args = {
        "command": command_name,
        "payload": {"chat_id": chat.chat_id, "message_id": message_id},
        "args": command_args,
        "gateway": "botvk",
      }

      response: ApiResponse = await self._api_client.exec(f"{plugin_name}.command", args=api_args)

    except asyncio.CancelledError:
      bot.context.logger.debug("Callback cancelled")

    except Exception as e:
      bot.context.logger.error(f"Callback exception {type(e).__name__}: {e}")
      await self._vk_api.send_message(chat.chat_id, "Error!")
