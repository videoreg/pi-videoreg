import json

from plugins.org_vrg_botvk.plugin import BotvkPlugin
from sdk.socket.api import ApiMethod


class MethodIsReadyToDie(ApiMethod):
  _plugin: BotvkPlugin

  def __init__(self, plugin: BotvkPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    alive_reasons = self._plugin.keep_alive.get_alive_reasons()
    return {
      "status": "ok",
      "ready": True if not alive_reasons else False,
      "why": json.dumps(alive_reasons),
    }
