import asyncio

import plugins.org_vrg_botvk.const as const
from plugins.org_vrg_botvk.keyboard import inline_callback_keyboard
from plugins.org_vrg_botvk.main import Bot
from plugins.org_vrg_botvk.plugin import BotvkPlugin
from plugins.org_vrg_botvk.vk_api import VkApi
from sdk.socket.api import ApiMethod


class MethodEditMessage(ApiMethod):
  _plugin: BotvkPlugin
  _bot: Bot
  _vk_api: VkApi

  def __init__(self, plugin: BotvkPlugin, bot: Bot, vk_api: VkApi):
    super().__init__()
    self._plugin = plugin
    self._bot = bot
    self._vk_api = vk_api

  async def exec(self, args):
    if not isinstance(args, dict):
      return {"status": "error", "error": "Arguments should be json"}

    payload = args.get("payload") or {}
    chat_id = payload.get("chat_id", self._bot.get_admin_chat().chat_id)
    # For VK this is the conversation_message_id carried from a callback event.
    message_id = payload.get("message_id")
    text = args.get("text")
    keyboard = args.get("keyboard")

    if not message_id:
      return {"status": "error", "error": "Missing message_id"}

    if not text:
      return {"status": "error", "error": "Missing text"}

    vk_keyboard = inline_callback_keyboard(keyboard)

    asyncio.create_task(self._do_edit_message(chat_id, message_id, text, vk_keyboard))

    return {"status": "ok"}

  async def _do_edit_message(self, chat_id, message_id, text, vk_keyboard):
    try:
      with self._plugin.keep_alive.wait_until_done(
        const.KEEP_ALIVE_WAIT_FINISH_OUTCOME_REQUEST_KEY, const.TIMEOUT_SEND_MESSAGE
      ):
        await self._vk_api.edit_message(chat_id, message_id, text, keyboard=vk_keyboard)

    except asyncio.CancelledError:
      self._plugin.logger.debug("edit message cancelled")

    except Exception as e:
      self._plugin.logger.error(f"edit message exception {type(e).__name__}: {e}")
