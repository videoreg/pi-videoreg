from plugins.org_vrg_bot.plugin import BotPlugin
from sdk.socket.api import ApiMethod


class MethodGetSettings(ApiMethod):
  _plugin: BotPlugin

  def __init__(self, plugin: BotPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    return {
      "status": "ok",
      "data": {
        "tg_bot_token": self._plugin.state.get("tg_bot_token", ""),
        "tg_bot_name": self._plugin.state.get("tg_bot_name", "Videoreg"),
      },
    }
