from plugins.org_vrg_rearcam.methods.common import parse_camera_number
from plugins.org_vrg_rearcam.plugin import RearcamPlugin
from sdk.socket.api import ApiMethod


class MethodGetConfig(ApiMethod):
  """Frame config of rear camera #N: args {"number": N}.

  Returns {"frame": {width,height,fps}, "frames": [...], "saved_frame": {...}?}.
  """

  _plugin: RearcamPlugin

  def __init__(self, plugin: RearcamPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    number = parse_camera_number(args)
    if number is None:
      return {"status": "error", "error": "invalid_number"}
    try:
      config = await self._plugin.get_camera_config(number)
      return {"status": "ok", "data": config}
    except Exception as e:
      self._plugin.logger.error(f"Error in get_config: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
