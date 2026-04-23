import asyncio
from pathlib import Path

import plugins.org_vrg_bot.const as const
from plugins.org_vrg_bot.main import Bot
from plugins.org_vrg_bot.plugin import BotPlugin
from plugins.org_vrg_bot.telegram_api import TelegramApi
from sdk.socket.api import ApiMethod


class MethodSendImage(ApiMethod):
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
    file_path_str = args.get("path")
    fallback_message = args.get("fallback_message")

    if not file_path_str:
      return {"status": "error", "error": "Missing file path"}

    file_path = Path(file_path_str)

    if not file_path.exists():
      return {"status": "error", "error": f"File does not exists {file_path_str}"}

    asyncio.create_task(self.do_send_photo(chat_id, file_path, fallback_message))

    return {"status": "ok"}

  async def do_send_photo(self, chat_id, photo_path, fallback_message):
    try:
      with self._plugin.keep_alive.wait_until_done(
        const.KEEP_ALIVE_WAIT_FINISH_OUTCOME_REQUEST_KEY, const.TIMEOUT_SEND_PHOTO
      ):
        await self._tg_api.send_chat_action(chat_id, "upload_photo")
        result = await self._tg_api.send_photo(chat_id, str(photo_path))

      if not result or result.get("ok") is not True:
        with self._plugin.keep_alive.wait_until_done(
          const.KEEP_ALIVE_WAIT_FINISH_OUTCOME_REQUEST_KEY, const.TIMEOUT_SEND_MESSAGE
        ):
          if fallback_message:
            await self._tg_api.send_message(chat_id, fallback_message)
          else:
            await self._tg_api.send_message(chat_id, "Error while sending photo")

    except asyncio.CancelledError:
      self._plugin.logger.warning("send photo cancelled")

    except Exception as e:
      self._plugin.logger.error(f"send photo exception {type(e).__name__}: {e}")
