"""Common functions for working with NetworkManager"""


class NetControls:
  async def is_network_manager_running(self) -> bool:
    raise NotImplementedError()

  async def get_wifi_radio_status(self) -> bool:
    raise NotImplementedError()

  async def set_connection_enabled(self, name: str, enabled: bool):
    raise NotImplementedError()

  async def set_wifi_blocked(self, blocked: bool):
    raise NotImplementedError()

  async def get_connection_info(self, connection_name: str, properties_map: dict = None) -> dict:
    raise NotImplementedError()

  async def get_wifi_credentials(self) -> dict:
    """SSID + PSK + local IP of the WiFi network the device itself is on.

    Returns {"mode": "ap"|"wifi", "ssid", "password", "ip"} or {} when neither
    the AP nor the WiFi-client profile is active. The password is a secret:
    never log it or pass it to the journal.
    """
    raise NotImplementedError()

  async def set_connection_property(self, connection_name: str, property_name: str, value: str):
    raise NotImplementedError()

  def get_nm_connections(self) -> list[dict]:
    raise NotImplementedError()
