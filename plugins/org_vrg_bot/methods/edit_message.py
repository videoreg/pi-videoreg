import asyncio
import json

import plugins.org_vrg_bot.const as const
from plugins.org_vrg_bot.main import Bot
from plugins.org_vrg_bot.plugin import BotPlugin
from plugins.org_vrg_bot.telegram_api import TelegramApi
from sdk.socket.api import ApiMethod


class MethodEditMessage(ApiMethod):
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
      return {"status": "error", "error": "Arguments should be json"}

    payload = args.get("payload") or {}
    chat_id = payload.get("chat_id", self._bot.get_admin_chat().chat_id)
    message_id = payload.get("message_id")
    text = args.get("text")
    keyboard = args.get("keyboard")

    if not message_id:
      return {"status": "error", "error": "Missing message_id"}

    if not text:
      return {"status": "error", "error": "Missing text"}

    reply_markup = json.dumps({"inline_keyboard": keyboard}) if keyboard else None

    asyncio.create_task(self._do_edit_message(chat_id, message_id, text, reply_markup))

    return {"status": "ok"}

  async def _do_edit_message(self, chat_id, message_id, text, reply_markup):
    try:
      with self._plugin.keep_alive.wait_until_done(
        const.KEEP_ALIVE_WAIT_FINISH_OUTCOME_REQUEST_KEY, const.TIMEOUT_SEND_MESSAGE
      ):
        await self._tg_api.edit_message_text(chat_id, message_id, text, reply_markup=reply_markup)

    except asyncio.CancelledError:
      self._plugin.logger.warning("edit message cancelled")

    except Exception as e:
      self._plugin.logger.error(f"edit message exception {type(e).__name__}: {e}")
