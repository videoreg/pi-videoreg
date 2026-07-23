import plugins.org_vrg_camera.const as const
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.socket.api import ApiMethod


class MethodSetStreamSettings(ApiMethod):
  """Saves stream-specific settings (camera_mode_str, video_width, video_height)"""

  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    if not isinstance(args, dict):
      return {"status": "error", "error": "args must be a dict"}

    camera_mode_str = args.get("stream_camera_mode_str")
    video_width = args.get("stream_video_width")
    video_height = args.get("stream_video_height")

    if not camera_mode_str or not isinstance(camera_mode_str, str):
      return {"status": "error", "error": "stream_camera_mode_str is required"}
    if not isinstance(video_width, int) or video_width <= 0:
      return {"status": "error", "error": "stream_video_width must be positive int"}
    if not isinstance(video_height, int) or video_height <= 0:
      return {"status": "error", "error": "stream_video_height must be positive int"}

    self._plugin.state.save(
      {
        const.KEY_STREAM_CAMERA_MODE_STR: camera_mode_str,
        const.KEY_STREAM_VIDEO_WIDTH: video_width,
        const.KEY_STREAM_VIDEO_HEIGHT: video_height,
      }
    )

    return {"status": "ok", "data": {}}
