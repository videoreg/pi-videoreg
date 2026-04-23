import asyncio

from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.socket.api import ApiMethod


class MethodVideoStart(ApiMethod):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    self._plugin.logger.info("Will start video from method")
    asyncio.create_task(self._plugin.start_video())
    return {"status": "ok", "bot_message": "Will start video"}
