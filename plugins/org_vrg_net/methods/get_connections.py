from plugins.org_vrg_net.net_controls import NetControls
from sdk.socket.api import ApiMethod


class MethodGetConnections(ApiMethod):
  _net_controls: NetControls

  def __init__(self, net_controls: NetControls):
    super().__init__()
    self._net_controls = net_controls

  async def exec(self, args):
    # Check WiFi radio status
    wifi_radio_enabled = await self._net_controls.get_wifi_radio_status()

    # Get AP connection info
    ap_info = await self._net_controls.get_connection_info(
      "ap",
      properties_map={
        "802-11-wireless.ssid": "ssid",
        # '802-11-wireless-security.psk': 'password'
      },
    )

    # Get WiFi client connection info
    wifi_info = await self._net_controls.get_connection_info(
      "wifi",
      properties_map={
        "802-11-wireless.ssid": "ssid",
        # '802-11-wireless-security.psk': 'password'
      },
    )

    # Get modem connection info
    modem_info = await self._net_controls.get_connection_info(
      "modem", properties_map={"gsm.apn": "apn"}
    )

    return {
      "status": "ok",
      "data": {
        "radio_enabled": wifi_radio_enabled,
        "ap": ap_info,
        "wifi": wifi_info,
        "modem": modem_info,
      },
    }
