import asyncio
import re

import plugins.org_vrg_camera.const as const
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.socket.api import ApiMethod


class MethodGetInfo(ApiMethod):
  """Returns camera info: model, recording state, video size"""

  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      model = await self._detect_camera_model()
      video_state = self._plugin.video_state.value
      video_size = self._plugin.state.get(const.KEY_VIDEO_SIZE, const.DEFAULT_VIDEO_SIZE)

      return {
        "status": "ok",
        "data": {
          "model": model,
          "video_state": video_state,
          "video_size": video_size,
          "fps": self._plugin.state.get(const.KEY_VIDEO_FPS, const.DEFAULT_VIDEO_FPS),
          "bitrate": self._plugin.state.get(const.KEY_VIDEO_BITRATE, const.DEFAULT_VIDEO_BITRATE),
          "camera_mode_str": self._plugin.state.get(
            const.KEY_CAMERA_MODE_STR, const.DEFAULT_CAMERA_MODE_STR
          ),
          "video_width": self._plugin.state.get(const.KEY_VIDEO_WIDTH, const.DEFAULT_VIDEO_WIDTH),
          "video_height": self._plugin.state.get(
            const.KEY_VIDEO_HEIGHT, const.DEFAULT_VIDEO_HEIGHT
          ),
          "hflip": self._plugin.state.get(const.KEY_HFLIP, const.DEFAULT_HFLIP),
          "vflip": self._plugin.state.get(const.KEY_VFLIP, const.DEFAULT_VFLIP),
          "screenshot": self._plugin.state.get(const.KEY_SCREENSHOT, const.DEFAULT_SCREENSHOT),
          "stream_camera_mode_str": self._plugin.state.get(const.KEY_STREAM_CAMERA_MODE_STR, const.DEFAULT_STREAM_CAMERA_MODE_STR),
          "stream_video_width": self._plugin.state.get(const.KEY_STREAM_VIDEO_WIDTH, const.DEFAULT_STREAM_VIDEO_WIDTH),
          "stream_video_height": self._plugin.state.get(const.KEY_STREAM_VIDEO_HEIGHT, const.DEFAULT_STREAM_VIDEO_HEIGHT),
        },
      }
    except Exception as e:
      self._plugin.logger.error(f"Error in get_info: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}

  async def _detect_camera_model(self):
    try:
      proc = await asyncio.create_subprocess_exec(
        "rpicam-hello",
        "--list-cameras",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
      )
      stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
      for line in stdout.decode(errors="replace").splitlines():
        match = re.search(r":\s+(\S+)\s+\[", line)
        if match:
          return match.group(1)
    except TimeoutError:
      self._plugin.logger.warning("get_info: rpicam-hello timed out")
    except Exception as e:
      self._plugin.logger.warning(f"get_info: failed to detect camera model: {e}")
    return None
