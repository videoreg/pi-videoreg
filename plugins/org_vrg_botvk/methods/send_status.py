import asyncio

from plugins.org_vrg_botvk.main import Bot
from plugins.org_vrg_botvk.plugin import BotvkPlugin
from plugins.org_vrg_botvk.vk_api import VkApi
from sdk.socket.api import ApiMethod

# VK messages.setActivity only supports "typing" and "audiomessage".
_ALLOWED_ACTIVITIES = {"typing", "audiomessage"}


class MethodSendStatus(ApiMethod):
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
      return {"status": "error", "error": "Arguments shuld be json"}

    payload = args.get("payload") or {}
    chat_id = payload.get("chat_id", self._bot.get_admin_chat().chat_id)
    status = args.get("status")

    if not status:
      return {"status": "error", "error": "Missing status"}

    activity = status if status in _ALLOWED_ACTIVITIES else "typing"

    asyncio.create_task(self._do_send_status(chat_id, activity))

    return {"status": "ok"}

  async def _do_send_status(self, chat_id, activity):
    try:
      await self._vk_api.set_activity(chat_id, activity)
    except asyncio.CancelledError:
      self._plugin.logger.warning("send status cancelled")

    except Exception as e:
      self._plugin.logger.error(f"send status exception {type(e).__name__}: {e}")
