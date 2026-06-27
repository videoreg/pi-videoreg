from plugins.org_vrg_botvk.plugin import BotvkPlugin
from sdk.socket.api import ApiMethod


class MethodGetSettings(ApiMethod):
  _plugin: BotvkPlugin

  def __init__(self, plugin: BotvkPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    return {
      "status": "ok",
      "data": {
        "vk_bot_token": self._plugin.state.get("vk_bot_token", ""),
        "vk_group_id": self._plugin.state.get("vk_group_id", ""),
      },
    }
