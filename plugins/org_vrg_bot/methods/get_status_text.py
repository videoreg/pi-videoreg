from plugins.org_vrg_bot.plugin import BotPlugin
from sdk.bot_health import format_health_text
from sdk.socket.api import ApiMethod


class MethodGetStatusText(ApiMethod):
  """Returns a short human-readable Telegram bot status for the `/status` summary."""

  _plugin: BotPlugin

  def __init__(self, plugin: BotPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      self._plugin.state.reload()
      configured = bool(self._plugin.state.get("tg_bot_token"))
      text = format_health_text("Telegram", configured, self._plugin.health)
      return {"status": "ok", "data": {"text": text}}
    except Exception as e:
      self._plugin.logger.error(f"Error in get_status_text: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
