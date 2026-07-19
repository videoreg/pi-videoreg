import plugins.org_vrg_camera.const as const
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.socket.api import ApiMethod

MIN_FILES = 1
# Hard upper bound guarding against absurd values. The disk-aware "smart" limit
# is enforced on the frontend (it depends on the fluctuating average file size);
# this is only a sanity cap.
MAX_FILES_HARD_CAP = 100000


class MethodSetFilesLimit(ApiMethod):
  """Saves the maximum number of stored H.264 files (with their companion MP4s)."""

  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    if not isinstance(args, dict):
      return {"status": "error", "error": "args must be a dict"}

    max_files = args.get("max_files")
    if isinstance(max_files, bool) or not isinstance(max_files, int):
      return {"status": "error", "error": "max_files must be an integer"}
    if max_files < MIN_FILES or max_files > MAX_FILES_HARD_CAP:
      return {
        "status": "error",
        "error": f"max_files must be between {MIN_FILES} and {MAX_FILES_HARD_CAP}",
      }

    self._plugin.state.save({const.KEY_MAX_H264_FILES: max_files})
    return {"status": "ok", "data": {"max_files": max_files}}
