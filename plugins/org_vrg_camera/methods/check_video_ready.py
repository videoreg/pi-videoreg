from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.socket.api import ApiMethod


class MethodCheckVideoReady(ApiMethod):
  """Checks whether MP4 is ready for the given video"""

  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      name = str(args.get("name", "")).strip()
      if not name:
        return {"status": "error", "error": "name required"}

      videoreg = self._plugin.runner.videoreg
      mp4_path = videoreg.mp4_path(f"{name}.mp4")
      ready = mp4_path.exists()

      return {"status": "ok", "data": {"ready": ready}}

    except Exception as e:
      self._plugin.logger.error(f"Error in check_video_ready: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
