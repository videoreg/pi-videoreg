from plugins.org_vrg_botvk.plugin import BotvkPlugin
from sdk.socket.api import ApiMethod


class MethodGetStatus(ApiMethod):
  """Bot health status: whether the bot exchanges data with the VK server.

  `healthy` is true only while the dispatcher polls and VK Long Poll has answered
  recently (even with no new events). This lets the UI show whether the bot is
  actually reachable, independent of user interaction.
  """

  _plugin: BotvkPlugin

  def __init__(self, plugin: BotvkPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    health = self._plugin.health
    self._plugin.state.reload()
    configured = bool(self._plugin.state.get("vk_bot_token")) and bool(
      self._plugin.state.get("vk_group_id")
    )
    return {
      "status": "ok",
      "data": {
        "configured": configured,
        "polling": health.polling,
        "healthy": health.is_healthy(),
        "last_ok_at": health.last_ok_at,
        "last_error": health.last_error,
      },
    }
