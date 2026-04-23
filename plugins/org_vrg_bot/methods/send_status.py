import asyncio

from plugins.org_vrg_bot.main import Bot
from plugins.org_vrg_bot.plugin import BotPlugin
from plugins.org_vrg_bot.telegram_api import TelegramApi
from sdk.socket.api import ApiMethod


class MethodSendStatus(ApiMethod):
  _plugin: BotPlugin
  _bot: Bot
  _tg_api: TelegramApi

  def __init__(self, plugin: BotPlugin, bot: Bot, tg_api: TelegramApi):
    super().__init__()
    self._plugin = plugin
    self._bot = bot
    self._tg_api = tg_api

  async def exec(self, args):
    if not isinstance(args, dict):
      return {"status": "error", "error": "Arguments shuld be json"}

    payload = args.get("payload", {})
    chat_id = payload.get("chat_id", self._bot.get_admin_chat().chat_id)
    status = args.get("status")

    if not status:
      return {"status": "error", "error": "Missing status"}

    asyncio.create_task(self._do_send_status(chat_id, status))

    return {"status": "ok"}

  async def _do_send_status(self, chat_id, status):
    try:
      await self._tg_api.send_chat_action(chat_id, status)
    except asyncio.CancelledError:
      self._plugin.logger.warning("send message cancelled")

    except Exception as e:
      self._plugin.logger.error(f"send message exception {type(e).__name__}: {e}")
