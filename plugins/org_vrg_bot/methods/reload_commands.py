from plugins.org_vrg_bot.plugin import BotPlugin
from sdk.socket.api import ApiMethod


class MethodReloadCommands(ApiMethod):
  """Rebuild the bot command list and re-push the Telegram menu.

  Plugins with dynamic menu commands (declared via `bot.menu_commands_method`,
  e.g. rearcam's /photo_N after pairing or forgetting a camera) call this to
  have their entries appear/disappear without a bot restart.
  """

  _plugin: BotPlugin

  def __init__(self, plugin: BotPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      names = await self._plugin.reload_commands()
      return {"status": "ok", "data": {"commands": names}}
    except Exception as e:
      self._plugin.logger.error(f"reload_commands failed: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
