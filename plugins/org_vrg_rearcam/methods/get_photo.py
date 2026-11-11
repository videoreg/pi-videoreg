from plugins.org_vrg_rearcam.methods.common import parse_camera_number
from plugins.org_vrg_rearcam.plugin import RearcamPlugin
from sdk.socket.api import ApiMethod


class MethodGetPhoto(ApiMethod):
  """Fetch a photo from rear camera #N: args {"number": N}.

  Returns {"path": <local jpeg path>} — the caller (e.g. the /photo command)
  sends the file and may delete it afterwards.
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
      path = await self._plugin.take_photo(number)
      return {"status": "ok", "data": {"path": path}}
    except Exception as e:
      self._plugin.logger.error(f"Error in get_photo: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
