from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.gateway import GatewayCommand


class CommandVideoStart(GatewayCommand):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, gateway, payload, args):
    await self._plugin.start_video()
    await gateway.send_text(payload=payload, text="Video started")
