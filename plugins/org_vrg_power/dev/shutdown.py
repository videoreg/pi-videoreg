from plugins.org_vrg_power.shutdown import ShutdownController, ShutdownLogic


class ShutdownLogicImpl(ShutdownLogic):
  async def should_shutdown(self, charging_status):
    return False


class ShutdownControllerImpl(ShutdownController):
  def get_wakeup_config(self):
    return {}


# Keep old names as aliases for backward compatibility
PisugarShutdownControllerImpl = ShutdownControllerImpl
