import os

from plugins.org_vrg_net.plugin import NetPlugin
from sdk.socket.api import ApiMethod

WG_CONFIG_PATH = "/etc/wireguard/wg0.conf"


class MethodSaveWireguardConfig(ApiMethod):
  """Writes the WireGuard config file (with a backup); moved from the http handler."""

  _plugin: NetPlugin

  def __init__(self, plugin: NetPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    content = args.get("content", "") if isinstance(args, dict) else ""

    if not content:
      return {"status": "error", "error": "Configuration content is required"}

    try:
      # Back up the existing config before overwriting
      if os.path.exists(WG_CONFIG_PATH):
        try:
          with open(WG_CONFIG_PATH, encoding="utf-8") as f:
            backup_content = f.read()
          with open(f"{WG_CONFIG_PATH}.backup", "w", encoding="utf-8") as f:
            f.write(backup_content)
        except Exception as e:
          self._plugin.logger.warning(f"Failed to create backup: {e}")

      with open(WG_CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(content)

      self._plugin.logger.info("WireGuard config file updated")
      return {"status": "ok", "data": {}}

    except PermissionError:
      self._plugin.logger.error(f"Permission denied writing to {WG_CONFIG_PATH}")
      return {"status": "error", "error": "Permission denied"}
    except Exception as e:
      self._plugin.logger.error(f"Error writing WireGuard config: {e}")
      return {"status": "error", "error": str(e)}
