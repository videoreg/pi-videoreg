from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.media_manager import MediaFileType
from sdk.socket.api import ApiMethod


class MethodRemoveFromFave(ApiMethod):
  """Removes a media file from the favourites folder"""

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
      self._plugin.delete_from_fave(name, fave_type)

      return {"status": "ok", "data": {}}

    except Exception as e:
      self._plugin.logger.error(f"Error in remove_from_fave: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
