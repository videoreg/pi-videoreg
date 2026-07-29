from plugins.org_vrg_botvk.plugin import BotvkPlugin
from sdk.bot_health import format_health_text
from sdk.socket.api import ApiMethod


class MethodGetStatusText(ApiMethod):
  """Returns a short human-readable VK bot status for the `/status` summary."""

  _plugin: BotvkPlugin

  def __init__(self, plugin: BotvkPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      self._plugin.state.reload()
      configured = bool(self._plugin.state.get("vk_bot_token")) and bool(
        self._plugin.state.get("vk_group_id")
      )
      text = format_health_text("VK", configured, self._plugin.health)
      return {"status": "ok", "data": {"text": text}}
    except Exception as e:
      self._plugin.logger.error(f"Error in get_status_text: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
