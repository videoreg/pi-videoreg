from plugins.org_vrg_net.net_controls import NetControls
from sdk.socket.api import ApiMethod


class MethodWifiCredentials(ApiMethod):
  """SSID + PSK + local IP of the WiFi network the device itself is on.

  Used by the rearcam plugin to provision cameras onto the same network
  (router or the device's own AP). Not exposed via HTTP — the PSK is a secret
  and must stay inside the backend.
  """

  def __init__(self, net_controls: NetControls):
    super().__init__()
    self._net_controls = net_controls

  async def exec(self, args):
    try:
      creds = await self._net_controls.get_wifi_credentials()
      if not creds:
        return {"status": "error", "error": "no_wifi_network"}
      return {"status": "ok", "data": creds}
    except Exception as e:
      return {"status": "error", "error": str(e)}
