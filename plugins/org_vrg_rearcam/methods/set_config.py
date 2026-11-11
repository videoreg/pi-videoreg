from plugins.org_vrg_rearcam.camera_client import CameraConfigError
from plugins.org_vrg_rearcam.methods.common import parse_camera_number
from plugins.org_vrg_rearcam.plugin import RearcamPlugin
from sdk.socket.api import ApiMethod


class MethodSetConfig(ApiMethod):
  """Set the frame size of rear camera #N: args {"number": N, "width": W, "height": H}.

  The camera switches its sensor format and persists it across reboots;
  the hub stores the choice in the device record.
  """

  _plugin: RearcamPlugin

  def __init__(self, plugin: RearcamPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    number = parse_camera_number(args)
    if number is None:
      return {"status": "error", "error": "invalid_number"}
    width = args.get("width") if isinstance(args, dict) else None
    height = args.get("height") if isinstance(args, dict) else None
    if not isinstance(width, int) or not isinstance(height, int):
      return {"status": "error", "error": "invalid_frame"}
    try:
      result = await self._plugin.set_camera_config(number, width, height)
      return {"status": "ok", "data": result}
    except CameraConfigError as e:
      return {"status": "error", "error": str(e)}
    except Exception as e:
      self._plugin.logger.error(f"Error in set_config: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
