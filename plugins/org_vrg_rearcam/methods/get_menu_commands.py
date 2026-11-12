from plugins.org_vrg_rearcam.plugin import RearcamPlugin
from sdk.socket.api import ApiMethod


class MethodGetMenuCommands(ApiMethod):
  """Dynamic gateway menu commands for the paired rear cameras (/photo_N).

  Declared in the manifest as `bot.menu_commands_method`; the bot gateway
  queries it when (re)building its command list (see bot.reload_commands).
  """

  _plugin: RearcamPlugin

  def __init__(self, plugin: RearcamPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    return {"status": "ok", "data": {"commands": self._plugin.menu_commands()}}
