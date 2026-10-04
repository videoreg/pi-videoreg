"""Outbound routing of a plugin's traffic: through WireGuard or the default interface.

Which plugins go through the tunnel is a setting of `org_vrg_net` (WireGuard settings ->
Routing). The tunnel is not the device's default route (see task/net/wg-routes.sh): a
connection goes through it only if its socket is bound to the tunnel's own address, for
which the system has a source-based routing rule. So a plugin that talks to the internet
creates its connections via `Egress`, which binds them to that address when the plugin is
routed through the tunnel, and leaves them unbound (default interface) otherwise.

When the tunnel is down or does not route the internet, `net.wg_egress` returns no address
and connections fall back to the default interface.

A plugin that uses `Egress` declares it in its `manifest.yaml`, so that it is listed on the
settings page:

    net:
      egress:
        title: $bot.telegram.menu   # i18n key (with "$") or plain text

Usage (aiohttp; a new session per request picks the current route up):

    async with aiohttp.ClientSession(connector=await plugin.egress.connector()) as session:
      ...

For other clients pass `await plugin.egress.local_address()` as the source address, e.g.
`asyncio.open_connection(host, port, local_addr=(address, 0))`.
"""

import socket
import time
from logging import Logger

import aiohttp

from sdk.socket.api import ApiClient

# How long a resolved route is reused before asking `net` again. A routing change made
# in the UI (or the tunnel going up/down) applies to new connections within this time.
CACHE_TTL = 10
REQUEST_TIMEOUT = 2


class Egress:
  _plugin_id: str
  _api_client: ApiClient
  _logger: Logger
  _address: str | None = None
  _expires_at: float = 0

  def __init__(self, plugin_id: str, api_client: ApiClient, logger: Logger):
    self._plugin_id = plugin_id
    self._api_client = api_client
    self._logger = logger

  async def local_address(self) -> str | None:
    """IPv4 address to bind outbound sockets to, or None to use the default interface"""
    now = time.monotonic()
    if now < self._expires_at:
      return self._address

    address = None
    try:
      response = await self._api_client.exec(
        "net.wg_egress", {"plugin": self._plugin_id}, timeout=REQUEST_TIMEOUT
      )
      if response.is_ok():
        address = (response.get_data() or {}).get("address")
      else:
        self._logger.warning(f"egress: net.wg_egress failed: {response.get_error()}")
    except Exception as e:
      # net is unavailable: use the default interface rather than block the plugin
      self._logger.warning(f"egress: net.wg_egress failed: {e}")

    if address != self._address:
      route = f"WireGuard ({address})" if address else "default interface"
      self._logger.info(f"egress: outbound traffic via {route}")

    self._address = address
    self._expires_at = now + CACHE_TTL
    return address

  async def connector(self) -> aiohttp.TCPConnector:
    """aiohttp connector for a new ClientSession (the session owns and closes it)"""
    address = await self.local_address()
    if not address:
      return aiohttp.TCPConnector()

    # IPv4 only: the tunnel address is IPv4, and an IPv6 connection could not use it
    return aiohttp.TCPConnector(local_addr=(address, 0), family=socket.AF_INET)
