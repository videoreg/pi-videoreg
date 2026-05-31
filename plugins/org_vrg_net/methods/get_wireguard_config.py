import os

from plugins.org_vrg_net.plugin import NetPlugin
from sdk.socket.api import ApiMethod

WG_CONFIG_PATH = "/etc/wireguard/wg0.conf"


class MethodGetWireguardConfig(ApiMethod):
  """Reads the WireGuard config file contents (moved from the http handler)."""

  _plugin: NetPlugin

  def __init__(self, plugin: NetPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      if not os.path.exists(WG_CONFIG_PATH):
        self._plugin.logger.warning(f"WireGuard config file not found: {WG_CONFIG_PATH}")
        return {"status": "ok", "data": {"content": "", "exists": False}}

      with open(WG_CONFIG_PATH, encoding="utf-8") as f:
        content = f.read()

      return {"status": "ok", "data": {"content": content, "exists": True}}

    except PermissionError:
      self._plugin.logger.error(f"Permission denied reading {WG_CONFIG_PATH}")
      return {"status": "error", "error": "Permission denied"}
    except Exception as e:
      self._plugin.logger.error(f"Error reading WireGuard config: {e}")
      return {"status": "error", "error": str(e)}
