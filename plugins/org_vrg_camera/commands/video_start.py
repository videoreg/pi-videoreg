from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.interface import InterfaceCommand


class CommandVideoStart(InterfaceCommand):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, interface, payload, args):
    await self._plugin.start_video()
    await interface.send_text(payload=payload, text="Video started")
