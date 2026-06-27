import asyncio

from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.gateway import Gateway, GatewayCommand


class CommandReboot(GatewayCommand):
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, gateway: Gateway, payload, args):
    asyncio.create_task(self._plugin.delayed_reboot())
