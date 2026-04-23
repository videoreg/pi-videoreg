import asyncio

from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.interface import Interface, InterfaceCommand


class CommandReboot(InterfaceCommand):
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, interface: Interface, payload, args):
    asyncio.create_task(self._plugin.delayed_reboot())
