import plugins.org_vrg_net.const as const
from plugins.org_vrg_net.plugin import NetPlugin
from sdk.merged_manifest import read_merged
from sdk.socket.api import ApiMethod


def read_egress_plugins(plugin: NetPlugin) -> list[dict]:
  """Plugins that declare `net.egress` in their manifest, i.e. route their outbound
  traffic via sdk/egress.py and can be sent through WireGuard."""
  result = []
  for entry in read_merged(plugin.runner.videoreg).get("plugins", []):
    egress = (entry.get("net") or {}).get("egress")
    if not egress:
      continue
    title = egress.get("title") if isinstance(egress, dict) else None
    result.append(
      {
        "id": entry.get("id"),
        "name": entry.get("name"),
        "title": title or entry.get("name"),
        "enabled": entry.get("enabled", True),
      }
    )
  return result


class MethodGetWireguardRouting(ApiMethod):
  """Returns which plugins send their outbound traffic through WireGuard, plus the state
  of the tunnel routing (whether that traffic can actually go through it right now)."""

  _plugin: NetPlugin

  def __init__(self, plugin: NetPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      selected = self._plugin.state.get(const.KEY_WG_EGRESS_PLUGINS, [])
      plugins = [{**p, "via_wg": p["id"] in selected} for p in read_egress_plugins(self._plugin)]

      monitor = self._plugin.wg_monitor
      active = await monitor.is_wg_active()
      info = await monitor.get_routing_info()

      return {
        "status": "ok",
        "data": {
          "plugins": plugins,
          "active": active,
          "address": info["address"],
          "routing": info["rule"],
          "default_route": info["default_route"],
        },
      }
    except Exception as e:
      self._plugin.logger.error(f"Error in wg_routing: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
