import os

import plugins.org_vrg_net.const as const
from plugins.org_vrg_net.plugin import NetPlugin
from plugins.org_vrg_net.wg_config import empty_settings, parse_config
from sdk.socket.api import ApiMethod


class MethodGetWireguardConfig(ApiMethod):
  """Returns the WireGuard form settings parsed from the config file.

  The private key is never sent to the client: the response carries `has_private_key` and
  the derived `public_key` instead (the one to register on the VPN server).
  """

  _plugin: NetPlugin

  def __init__(self, plugin: NetPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      if not os.path.exists(const.WG_CONFIG_PATH):
        settings = empty_settings()
        settings.pop("private_key")
        return {
          "status": "ok",
          "data": {
            "exists": False,
            "settings": settings,
            "has_private_key": False,
            "public_key": None,
          },
        }

      with open(const.WG_CONFIG_PATH, encoding="utf-8") as f:
        settings, _ = parse_config(f.read())

      private_key = settings.pop("private_key")
      public_key = None
      if private_key:
        public_key = await self._plugin.wg_monitor.get_public_key(private_key)

      return {
        "status": "ok",
        "data": {
          "exists": True,
          "settings": settings,
          "has_private_key": bool(private_key),
          "public_key": public_key,
        },
      }

    except PermissionError:
      self._plugin.logger.error(f"Permission denied reading {const.WG_CONFIG_PATH}")
      return {"status": "error", "error": "Permission denied"}
    except Exception as e:
      self._plugin.logger.error(f"Error reading WireGuard config: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
