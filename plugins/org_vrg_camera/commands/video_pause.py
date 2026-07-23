from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.gateway import GatewayCommand


class CommandVideoPause(GatewayCommand):
  _plugin: CameraPlugin

  def __init__(self, service: CameraPlugin):
    super().__init__()
    self._plugin = service

  async def exec(self, gateway, payload, args):
    await self._plugin.stop_video(pause=True)
    await gateway.send_text(payload=payload, text="Video paused")
