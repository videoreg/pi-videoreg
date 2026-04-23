from plugins.org_vrg_power.shutdown import PisugarShutdownController, ShutdownLogic


class ShutdownLogicImpl(ShutdownLogic):
  async def should_shutdown(self, is_charging):
    return False


class PisugarShutdownControllerImpl(PisugarShutdownController):
  def get_wakeup_config(self):
    return {}
