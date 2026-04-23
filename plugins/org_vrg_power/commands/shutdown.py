import asyncio

import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from plugins.org_vrg_power.shutdown import PisugarShutdownController
from sdk.interface import Interface, InterfaceCommand


class CommandShutdown(InterfaceCommand):
  _plugin: PowerPlugin
  _shutdown_controller: PisugarShutdownController
  _force_wakeup_config: str = None

  def __init__(
    self,
    plugin: PowerPlugin,
    shutdown_controller: PisugarShutdownController,
    force_wakeup_config: str = None,
  ):
    super().__init__()
    self._plugin = plugin
    self._shutdown_controller = shutdown_controller
    self._force_wakeup_config = force_wakeup_config

  async def exec(self, interface: Interface, payload, args):
    reason = args if isinstance(args, str) else "unknown"
    shutdown_config = await self._shutdown_controller.shutdown(reason, self._force_wakeup_config)
    if shutdown_config:
      self._plugin.state.save({const.STATE_KEY_LAST_SHUTDOWN_CONFIG: shutdown_config.to_json()})
      await interface.send_text(payload, "Will shudown")
      asyncio.create_task(self._plugin.delayed_shutdown())
    else:
      self._plugin.logger.warning("Command CommandShutdown error")
      await interface.send_text(payload, "Shutdown error")
