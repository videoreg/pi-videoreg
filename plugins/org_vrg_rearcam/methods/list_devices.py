from plugins.org_vrg_rearcam.plugin import RearcamPlugin
from sdk.socket.api import ApiMethod


class MethodListDevices(ApiMethod):
  """List paired rear cameras with their runtime online state."""

  _plugin: RearcamPlugin

  def __init__(self, plugin: RearcamPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      return {"status": "ok", "data": {"devices": self._plugin.list_devices()}}
    except Exception as e:
      self._plugin.logger.error(f"Error in list_devices: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
