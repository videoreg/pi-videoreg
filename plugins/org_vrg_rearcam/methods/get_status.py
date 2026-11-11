from plugins.org_vrg_rearcam.plugin import RearcamPlugin
from sdk.socket.api import ApiMethod


class MethodGetStatus(ApiMethod):
  """Live status of rear camera #N (health + status merged): args {"number": N}."""

  _plugin: RearcamPlugin

  def __init__(self, plugin: RearcamPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    number = args.get("number") if isinstance(args, dict) else None
    if not isinstance(number, int) or number < 2:
      return {"status": "error", "error": "invalid_number"}
    try:
      status = await self._plugin.get_camera_status(number)
      return {"status": "ok", "data": status}
    except Exception as e:
      self._plugin.logger.error(f"Error in get_status: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
