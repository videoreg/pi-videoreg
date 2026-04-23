class WireguardMonitorImpl:
  def get_active_connections(self):
    return []

  def is_wifi_connected(self, connections: list) -> bool:
    return True

  def is_modem_active(self, connections: list) -> bool:
    return False

  def is_wg_configured(self) -> bool:
    return False

  async def is_wg_active(self) -> bool:
    return False

  async def start_wireguard(self):
    pass

  async def stop_wireguard(self):
    pass

  async def get_wg_info(self) -> dict:
    return {}

  async def notify_wg_enabled(self):
    pass

  async def notify_wg_disabled(self):
    pass

  async def start_monitor_loop(self):
    pass

  def stop_monitor_loop(self):
    pass
