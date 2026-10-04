from dataclasses import dataclass


@dataclass
class Config:
  connection_name_wifi: str
  connection_name_modem: str
  wg_interface: str
  wg_config_path: str
  check_interval: int


class WireguardMonitor:
  # When True, WireGuard is stopped while the "wifi" client connection is active.
  # When False, WireGuard stays up regardless of the WiFi client connection.
  skip_on_wifi: bool = True

  def get_active_connections(self):
    """Gets the list of active connections"""
    raise NotImplementedError()

  def is_wifi_connected(self, connections: list) -> bool:
    """Checks whether WiFi is connected"""
    raise NotImplementedError()

  def is_modem_active(self, connections: list) -> bool:
    """Checks whether the modem is active"""
    raise NotImplementedError()

  def is_wg_configured(self) -> bool:
    """Checks whether WireGuard is configured"""
    raise NotImplementedError()

  async def is_wg_active(self) -> bool:
    """Checks whether WireGuard is running (async)"""
    raise NotImplementedError()

  async def start_wireguard(self):
    """Starts WireGuard (async)"""
    raise NotImplementedError()

  async def stop_wireguard(self):
    """Stops WireGuard (async)"""
    raise NotImplementedError()

  async def get_wg_info(self) -> dict:
    """
    Gets information about the WireGuard connection.

    Returns:
        dict with fields:
        - active (bool): whether the interface is active
        - interface (str): interface name
        - ip_address (str): interface IP address or None
        - public_key (str): public key or None
        - listening_port (int): listening port or None
        - peers (list): list of connected peers with their parameters
    """
    raise NotImplementedError()

  async def get_routing_info(self, cached: bool = False) -> dict:
    """
    Gets the state of the source-based routing set up by task/net/wg-routes.sh.
    With cached=True, may return a recent result instead of querying the kernel.

    Returns:
        dict with fields:
        - address (str): IPv4 address of the interface (without mask) or None
        - rule (bool): whether traffic sourced from the address is routed into the tunnel table
        - default_route (bool): whether the tunnel table has a default route, i.e. the peer's
          AllowedIPs include 0.0.0.0/0 and arbitrary internet hosts are reachable through it
    """
    raise NotImplementedError()

  async def restart_wireguard(self):
    """Brings WireGuard down (if it is up) and up again, e.g. to apply a new config (async)"""
    raise NotImplementedError()

  async def get_public_key(self, private_key: str) -> str | None:
    """Derives the public key from a private key (`wg pubkey`)"""
    raise NotImplementedError()

  async def notify_wg_enabled(self):
    pass

  async def notify_wg_disabled(self):
    pass

  async def start_monitor_loop(self):
    raise NotImplementedError()

  def stop_monitor_loop(self):
    raise NotImplementedError()
