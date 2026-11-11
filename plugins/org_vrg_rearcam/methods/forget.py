from plugins.org_vrg_rearcam.plugin import RearcamPlugin
from sdk.socket.api import ApiMethod


class MethodForget(ApiMethod):
  """Remove a paired rear camera: args {"number": N}."""

  _plugin: RearcamPlugin

  def __init__(self, plugin: RearcamPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    number = args.get("number") if isinstance(args, dict) else None
    if not isinstance(number, int) or number < 2:
      return {"status": "error", "error": "invalid_number"}
    try:
      if not self._plugin.forget(number):
        return {"status": "error", "error": "camera_not_found"}
      return {"status": "ok", "data": {"devices": self._plugin.list_devices()}}
    except Exception as e:
      self._plugin.logger.error(f"Error in forget: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
