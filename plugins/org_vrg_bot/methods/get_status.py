from plugins.org_vrg_bot.plugin import BotPlugin
from sdk.socket.api import ApiMethod


class MethodGetStatus(ApiMethod):
  """Bot health status: whether the bot exchanges data with the Telegram server.

  `healthy` is true only while the dispatcher polls and Telegram has answered a
  getUpdates request (even an empty one) recently. This lets the UI show whether
  the bot is actually reachable, independent of user interaction.
  """

  _plugin: BotPlugin

  def __init__(self, plugin: BotPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    health = self._plugin.health
    self._plugin.state.reload()
    configured = bool(self._plugin.state.get("tg_bot_token"))
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
