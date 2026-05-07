import plugins.org_vrg_net.ip as ip
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.interface import Interface, InterfaceCommand

RTSP_PORT = 8554
RTSP_PATH = "videoreg"


class CommandStream(InterfaceCommand):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, interface: Interface, payload, args):
    await self._plugin.stream_start()
    current_ip = ip.get_current_ip()
    await interface.send_text(payload, f"rtsp://{current_ip}:{RTSP_PORT}/{RTSP_PATH}")
