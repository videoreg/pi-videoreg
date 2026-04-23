from plugins.org_vrg_net.net_controls import NetControls


class NetControlsImpl(NetControls):
  async def get_wifi_radio_status(self) -> bool:
    return True

  async def set_connection_enabled(self, name: str, enabled: bool):
    pass

  async def set_wifi_blocked(self, blocked: bool):
    pass

  async def get_connection_info(self, connection_name: str, properties_map: dict = None) -> dict:
    return {}

  async def set_connection_property(self, connection_name: str, property_name: str, value: str):
    pass

  def get_nm_connections(self) -> list[dict]:
    return []
