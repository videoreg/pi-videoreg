import asyncio

from plugins.org_vrg_net.net_controls import NetControls
from sdk.socket.api import ApiMethod


class MethodGetConnections(ApiMethod):
  _net_controls: NetControls

  def __init__(self, net_controls: NetControls):
    super().__init__()
    self._net_controls = net_controls

  async def exec(self, args):
    # Each of these spawns an nmcli subprocess; run them concurrently so the
    # total latency is the slowest single call, not their sum. At boot / first
    # page load NetworkManager is slow to answer, and the sequential version
    # overran the dashboard timeout, dropping the block (the tile then falsely
    # rendered as "disconnected"). Each helper swallows its own errors and
    # returns a default, so a plain gather never raises here.
    #
    # - AP / WiFi client connection info (radio status + ssid).
    # - modem connection info (IP/device only; APN is configured over AT in the
    #   modem plugin, not via the NetworkManager gsm profile).
    wifi_radio_enabled, ap_info, wifi_info, modem_info = await asyncio.gather(
      self._net_controls.get_wifi_radio_status(),
      self._net_controls.get_connection_info(
        "ap",
        properties_map={
          "802-11-wireless.ssid": "ssid",
          # '802-11-wireless-security.psk': 'password'
        },
      ),
      self._net_controls.get_connection_info(
        "wifi",
        properties_map={
          "802-11-wireless.ssid": "ssid",
          # '802-11-wireless-security.psk': 'password'
        },
      ),
      self._net_controls.get_connection_info("modem"),
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
