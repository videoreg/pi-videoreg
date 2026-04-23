import asyncio

import plugins.org_vrg_camera.const as const
from plugins.org_vrg_camera.plugin import CameraPlugin, VideoState
from sdk.socket.api import ApiMethod

ALLOWED_FPS = [15, 30]
ALLOWED_BITRATES = [2000000, 3000000, 4000000, 5000000]


class MethodSetVideoSettings(ApiMethod):
  """Saves video settings (fps, bitrate, camera_mode_str, width, height)"""

  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    if not isinstance(args, dict):
      return {"status": "error", "error": "args must be a dict"}

    fps = args.get("fps")
    bitrate = args.get("bitrate")
    camera_mode_str = args.get("camera_mode_str")
    video_width = args.get("video_width")
    video_height = args.get("video_height")

    if fps not in ALLOWED_FPS:
      return {"status": "error", "error": f"fps must be one of {ALLOWED_FPS}"}
    if bitrate not in ALLOWED_BITRATES:
      return {"status": "error", "error": f"bitrate must be one of {ALLOWED_BITRATES}"}
    if not camera_mode_str or not isinstance(camera_mode_str, str):
      return {"status": "error", "error": "camera_mode_str is required"}
    if not isinstance(video_width, int) or video_width <= 0:
      return {"status": "error", "error": "video_width must be positive int"}
    if not isinstance(video_height, int) or video_height <= 0:
      return {"status": "error", "error": "video_height must be positive int"}

    hflip = args.get("hflip", False)
    vflip = args.get("vflip", False)
    screenshot = args.get("screenshot", True)

    if not isinstance(hflip, bool):
      return {"status": "error", "error": "hflip must be bool"}
    if not isinstance(vflip, bool):
      return {"status": "error", "error": "vflip must be bool"}
    if not isinstance(screenshot, bool):
      return {"status": "error", "error": "screenshot must be bool"}

    self._plugin.state.save(
      {
        const.KEY_VIDEO_FPS: fps,
        const.KEY_VIDEO_BITRATE: bitrate,
        const.KEY_CAMERA_MODE_STR: camera_mode_str,
        const.KEY_VIDEO_WIDTH: video_width,
        const.KEY_VIDEO_HEIGHT: video_height,
        const.KEY_HFLIP: hflip,
        const.KEY_VFLIP: vflip,
        const.KEY_SCREENSHOT: screenshot,
      }
    )

    if self._plugin.video_state == VideoState.START:
      asyncio.create_task(self._plugin.restart_video())

    return {"status": "ok", "data": {}}
