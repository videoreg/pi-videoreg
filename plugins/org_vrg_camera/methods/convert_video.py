import asyncio

from plugins.org_vrg_camera.convert import convert_h264_to_mp4
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.socket.api import ApiMethod


class MethodConvertVideo(ApiMethod):
  """Starts H.264 → MP4 conversion in the background; does not block the response"""

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
      if mp4_path.exists():
        return {"status": "ok", "message": "already_ready"}

      if name in self._plugin._converting_names:
        return {"status": "ok", "message": "already_converting"}

      self._plugin._converting_names.add(name)
      asyncio.create_task(self._do_convert(name))
      return {"status": "ok", "message": "started"}

    except Exception as e:
      self._plugin.logger.error(f"Error in convert_video: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}

  async def _do_convert(self, name: str):
    try:
      videoreg = self._plugin.runner.videoreg
      h264_path = videoreg.h264_path(f"{name}.h264")
      mp4_path = videoreg.mp4_path(f"{name}.mp4")

      await self._plugin.suspend_video()
      await convert_h264_to_mp4(self._plugin, h264_path, mp4_path)
      await self._plugin.continue_video()
    except Exception as e:
      self._plugin.logger.error(f"Error converting video '{name}': {e}", exc_info=True)
    finally:
      self._plugin._converting_names.discard(name)
