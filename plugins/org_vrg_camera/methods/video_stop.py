import asyncio

from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.socket.api import ApiMethod


class MethodVideoStop(ApiMethod):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    self._plugin.logger.info("Will stop video from method")
    asyncio.create_task(self._plugin.stop_video())
    return {"status": "ok", "bot_message": "Will stop video"}
