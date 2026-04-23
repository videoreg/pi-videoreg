import json

from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.socket.api import ApiMethod


class MethodIsReadyToDie(ApiMethod):
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    alive_reasons = self._plugin.keep_alive.get_alive_reasons()
    return {"status": "ok", "ready": not bool(alive_reasons), "why": json.dumps(alive_reasons)}
