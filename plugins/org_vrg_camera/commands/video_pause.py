from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.interface import InterfaceCommand


class CommandVideoPause(InterfaceCommand):
  _plugin: CameraPlugin

  def __init__(self, service: CameraPlugin):
    super().__init__()
    self._plugin = service

  async def exec(self, interface, payload, args):
    await self._plugin.stop_video(pause=True)
    await interface.send_text(payload=payload, text="Video paused")
