import asyncio

import plugins.org_vrg_net.const as const
from plugins.org_vrg_net.plugin import NetPlugin
from sdk.socket.api import ApiMethod


class MethodWgAuto(ApiMethod):
  _plugin: NetPlugin

  def __init__(self, plugin: NetPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    enable = True if args == "enable" else False

    self._plugin.state.save({const.KEY_WG_AUTO: enable})

    if enable:
      asyncio.create_task(self._plugin.start_wg_monitor_loop())
    else:
      self._plugin.stop_wg_monitor_loop()

    return {"status": "ok", "enabled": enable}
