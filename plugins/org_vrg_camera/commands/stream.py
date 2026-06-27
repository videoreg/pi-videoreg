import plugins.org_vrg_net.ip as ip
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.gateway import Gateway, GatewayCommand

RTSP_PORT = 8554
RTSP_PATH = "videoreg"


class CommandStream(GatewayCommand):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, gateway: Gateway, payload, args):
    await self._plugin.stream_start()
    current_ip = ip.get_current_ip()
    await gateway.send_text(payload, f"rtsp://{current_ip}:{RTSP_PORT}/{RTSP_PATH}")
