"""Common functions for working with NetworkManager"""


class NetControls:
  async def get_wifi_radio_status(self) -> bool:
    raise NotImplementedError()

  async def set_connection_enabled(self, name: str, enabled: bool):
    raise NotImplementedError()

  async def set_wifi_blocked(self, blocked: bool):
    raise NotImplementedError()

  async def get_connection_info(self, connection_name: str, properties_map: dict = None) -> dict:
    raise NotImplementedError()

  async def set_connection_property(self, connection_name: str, property_name: str, value: str):
    raise NotImplementedError()

  def get_nm_connections(self) -> list[dict]:
    raise NotImplementedError()
