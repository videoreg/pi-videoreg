from plugins.org_vrg_net.plugin import NetPlugin
from sdk.socket.api import ApiMethod


class MethodWgShow(ApiMethod):
  _plugin: NetPlugin

  def __init__(self, plugin: NetPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    wg_info = await self._plugin.wg_monitor.get_wg_info()

    return {
      "status": "ok",
      "wg_info": wg_info,
    }
