import asyncio

from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.service import ApiMethod


class MethodVideoPause(ApiMethod):
  _plugin: CameraPlugin

  def __init__(self, service: CameraPlugin):
    super().__init__()
    self._plugin = service

  async def exec(self, args):
    self._plugin.logger.info("Will pause video from method")
    asyncio.create_task(self._plugin.stop_video(pause=True))
    return {"status": "ok", "bot_message": "Will pause video"}
