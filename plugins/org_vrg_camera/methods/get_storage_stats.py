import os
import shutil

import plugins.org_vrg_camera.const as const
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.media_manager import MediaFileType
from sdk.socket.api import ApiMethod


class MethodGetStorageStats(ApiMethod):
  """Returns storage statistics for the H.264 file limit UI.

  The frontend caches these values once and recomputes the estimated disk
  footprint of an arbitrary file count locally (without hitting the backend on
  every keystroke). `avg_file_bytes` is measured from existing recordings, or
  estimated from the current bitrate when no recordings exist yet.
  """

  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      h264_dir = str(self._plugin.runner.media_manager.get_dir(MediaFileType.H264))
      count, total_bytes = self._scan_dir(h264_dir)

      if count > 0:
        avg_file_bytes = total_bytes / count
      else:
        # No recordings yet — estimate a segment size from the current bitrate.
        bitrate = self._plugin.state.get(const.KEY_VIDEO_BITRATE, const.DEFAULT_VIDEO_BITRATE)
        avg_file_bytes = bitrate / 8 * const.H264_SEGMENT_SECONDS

      try:
        disk_total_bytes = shutil.disk_usage(h264_dir).total
      except Exception:
        disk_total_bytes = 0

      return {
        "status": "ok",
        "data": {
          "max_files": self._plugin.state.get(
            const.KEY_MAX_H264_FILES, const.DEFAULT_MAX_H264_FILES
          ),
          "h264_count": count,
          "h264_total_bytes": total_bytes,
          "avg_file_bytes": avg_file_bytes,
          "disk_total_bytes": disk_total_bytes,
          "disk_reserve_fraction": const.DISK_RESERVE_FRACTION,
        },
      }
    except Exception as e:
      self._plugin.logger.error(f"Error in get_storage_stats: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}

  @staticmethod
  def _scan_dir(dir_path: str) -> tuple[int, int]:
    """Returns (file count, total size in bytes) for the given directory."""
    count = 0
    total = 0
    try:
      with os.scandir(dir_path) as it:
        for entry in it:
          if not entry.is_file():
            continue
          try:
            total += entry.stat().st_size
            count += 1
          except OSError:
            pass
    except OSError:
      pass
    return count, total
