from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.media_manager import MediaFileType
from sdk.socket.api import ApiMethod


class MethodAddToFave(ApiMethod):
  """Copies a media file to the favourites folder"""

  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      if not isinstance(args, dict):
        args = {}

      file_type = args.get("type", "")
      name = args.get("name", "")

      if file_type not in ("h264", "jpeg"):
        return {"status": "error", "error": f"Invalid type: {file_type}"}

      if not name:
        return {"status": "error", "error": "name is required"}

      fave_type = MediaFileType.H264_FAVE if file_type == "h264" else MediaFileType.JPEG_FAVE
      found = self._plugin.copy_to_fave(name, fave_type)

      if not found:
        return {"status": "error", "error": f"File not found: {name}"}

      return {"status": "ok", "data": {}}

    except Exception as e:
      self._plugin.logger.error(f"Error in add_to_fave: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
