import os
from datetime import datetime

from plugins.org_vrg_gps.plugin import GpsPlugin
from sdk.media_manager import MediaFileType
from sdk.socket.api import ApiMethod


class MethodGetTracks(ApiMethod):
  """Returns list of GPX tracks"""

  _plugin: GpsPlugin

  def __init__(self, plugin: GpsPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    media_manager = self._plugin.runner.media_manager
    gps_dir = media_manager.get_dir(MediaFileType.GPS)
    tracks = []

    try:
      files = sorted(
        [f for f in media_manager.get_files(MediaFileType.GPS) if f.endswith(".gpx")], reverse=True
      )

      for filename in files:
        stem = filename[:-4]  # strip .gpx
        try:
          dt = datetime.strptime(stem, "%Y-%m-%d_%H-%M-%S")
          date_str = dt.strftime("%Y-%m-%d")
          time_str = dt.strftime("%H:%M:%S")
        except ValueError:
          # fallback: use file modification time
          try:
            mtime = os.path.getmtime(str(gps_dir / filename))
            dt = datetime.fromtimestamp(mtime)
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M:%S")
          except Exception:
            date_str = ""
            time_str = ""

        tracks.append({"filename": stem, "date": date_str, "time": time_str})

      return {"status": "ok", "data": {"tracks": tracks}}
    except Exception as e:
      self._plugin.logger.error(f"Error in get_tracks: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
