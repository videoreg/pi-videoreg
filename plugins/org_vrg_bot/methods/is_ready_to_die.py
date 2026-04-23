import json

from plugins.org_vrg_bot.plugin import BotPlugin
from sdk.socket.api import ApiMethod


class MethodIsReadyToDie(ApiMethod):
  _plugin: BotPlugin
  _wait_network_limit = 20
  _wait_first_request_limit = 10
  _wait_user_interaction = 60

  def __init__(self, plugin: BotPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    alive_reasons = self._plugin.keep_alive.get_alive_reasons()
    return {
      "status": "ok",
      "ready": True if not alive_reasons else False,
      "why": json.dumps(alive_reasons),
    }
