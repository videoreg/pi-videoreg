import asyncio
from pathlib import Path

import plugins.org_vrg_botvk.const as const
from plugins.org_vrg_botvk.main import Bot
from plugins.org_vrg_botvk.plugin import BotvkPlugin
from plugins.org_vrg_botvk.vk_api import VkApi
from sdk.socket.api import ApiMethod


class MethodSendDocument(ApiMethod):
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
    file_path_str = args.get("path")
    fallback_message = args.get("fallback_message")

    if not file_path_str:
      return {"status": "error", "error": "Missing file path"}

    file_path = Path(file_path_str)

    if not file_path.exists():
      self._plugin.logger.error(f"send_document: file does not exist for botvk: {file_path_str}")
      return {"status": "error", "error": f"File does not exists {file_path_str}"}

    self._plugin.logger.info(f"send_document: sending {file_path_str} to {chat_id}")
    asyncio.create_task(self._do_send(chat_id, file_path, fallback_message))

    return {"status": "ok"}

  async def _do_send(self, chat_id, file_path, fallback_message):
    try:
      with self._plugin.keep_alive.wait_until_done(
        const.KEEP_ALIVE_WAIT_FINISH_OUTCOME_REQUEST_KEY, const.TIMEOUT_SEND_DOCUMENT
      ):
        attachment = await self._vk_api.upload_document(chat_id, str(file_path))
        self._plugin.logger.info(f"document upload attachment={attachment}")
        result = None
        if attachment:
          result = await self._vk_api.send_message(chat_id, "", attachment=attachment)

      ok = isinstance(result, dict) and "response" in result
      if not ok:
        self._plugin.logger.error(
          f"send document failed: attachment={attachment} result={result}"
        )
        with self._plugin.keep_alive.wait_until_done(
          const.KEEP_ALIVE_WAIT_FINISH_OUTCOME_REQUEST_KEY, const.TIMEOUT_SEND_MESSAGE
        ):
          if fallback_message:
            await self._vk_api.send_message(chat_id, fallback_message)
          else:
            await self._vk_api.send_message(chat_id, f"Error while uploading {file_path}")

    except asyncio.CancelledError:
      self._plugin.logger.warning("send document cancelled")

    except Exception as e:
      self._plugin.logger.error(f"send document exception {type(e).__name__}: {e}")
