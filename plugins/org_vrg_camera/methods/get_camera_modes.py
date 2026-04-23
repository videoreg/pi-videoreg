import asyncio
import re

from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.socket.api import ApiMethod


class MethodGetCameraModes(ApiMethod):
  """Returns the list of available camera modes from rpicam-hello --list-cameras"""

  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    modes = await self._get_modes()
    return {"status": "ok", "data": {"modes": modes}}

  async def _get_modes(self):
    try:
      proc = await asyncio.create_subprocess_exec(
        "rpicam-hello",
        "--list-cameras",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
      )
      stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
      return self._parse_modes(stdout.decode(errors="replace"))
    except Exception as e:
      self._plugin.logger.warning(f"get_camera_modes: failed: {e}")
      return []

  def _parse_modes(self, output: str):
    modes = []
    seen = set()
    for match in re.finditer(r"(\d+)x(\d+)\s+\[(\d+(?:\.\d+)?)\s+fps", output):
      width = int(match.group(1))
      height = int(match.group(2))
      max_fps = float(match.group(3))
      key = (width, height)
      if key in seen:
        continue
      seen.add(key)
      fps_int = int(max_fps)
      modes.append(
        {
          "mode_str": f"{width}:{height}",
          "width": width,
          "height": height,
          "max_fps": max_fps,
          "label": f"{width}\u00d7{height} (max {fps_int} fps)",
        }
      )
    return modes
