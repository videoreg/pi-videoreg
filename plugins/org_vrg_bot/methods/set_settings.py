from plugins.org_vrg_bot.plugin import BotPlugin
from plugins.org_vrg_bot.telegram_api import TelegramApi
from sdk.socket.api import ApiMethod


class MethodSetSettings(ApiMethod):
  _plugin: BotPlugin
  _tg_api: TelegramApi

  def __init__(self, plugin: BotPlugin, tg_api: TelegramApi):
    super().__init__()
    self._plugin = plugin
    self._tg_api = tg_api

  async def exec(self, args):
    if not isinstance(args, dict):
      return {"status": "error", "error": "Arguments should be json"}

    patch = {}

    tg_bot_token = args.get("tg_bot_token")
    if tg_bot_token is not None:
      patch["tg_bot_token"] = str(tg_bot_token).strip()

    tg_bot_name = args.get("tg_bot_name")
    if tg_bot_name is not None:
      patch["tg_bot_name"] = str(tg_bot_name).strip()

    if not patch:
      return {"status": "error", "error": "No fields to update"}

    self._plugin.state.save(patch)

    if "tg_bot_name" in patch:
      await self._tg_api.set_my_name(patch["tg_bot_name"])

    return {"status": "ok"}
