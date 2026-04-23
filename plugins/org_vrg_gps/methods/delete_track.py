import os

from plugins.org_vrg_gps.plugin import GpsPlugin
from sdk.media_manager import MediaFileType
from sdk.socket.api import ApiMethod


class MethodDeleteTrack(ApiMethod):
  """Deletes a GPX track by filename"""

  _plugin: GpsPlugin

  def __init__(self, plugin: GpsPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    filename = (args or {}).get("filename", "")

    if not filename or "/" in filename or "\\" in filename or ".." in filename:
      return {"status": "error", "error": "Invalid filename"}

    try:
      media_manager = self._plugin.runner.media_manager
      gps_dir = media_manager.get_dir(MediaFileType.GPS)
      file_path = gps_dir / f"{filename}.gpx"

      if not file_path.exists():
        return {"status": "error", "error": "Track not found"}

      os.remove(str(file_path))
      media_manager.invalidate(MediaFileType.GPS)
      return {"status": "ok", "data": {}}
    except Exception as e:
      self._plugin.logger.error(f"Error in delete_track: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
