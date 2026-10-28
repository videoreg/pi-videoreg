import plugins.org_vrg_net.const as const
from plugins.org_vrg_net.methods.get_wireguard_routing import read_egress_plugins
from plugins.org_vrg_net.plugin import NetPlugin
from sdk.socket.api import ApiMethod


class MethodSetWireguardRouting(ApiMethod):
  """Sends a plugin's outbound traffic through WireGuard or the default interface.

  Args: {"plugin": <plugin id>, "via_wg": bool}
  Plugins pick the change up within the sdk/egress.py cache time.
  """

  _plugin: NetPlugin

  def __init__(self, plugin: NetPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    if not isinstance(args, dict):
      return {"status": "error", "error": "Arguments are required"}

    plugin_id = args.get("plugin")
    via_wg = bool(args.get("via_wg"))

    try:
      if plugin_id not in [p["id"] for p in read_egress_plugins(self._plugin)]:
        return {"status": "error", "error": f"Unknown plugin: {plugin_id}"}

      selected = self._plugin.state.get(const.KEY_WG_EGRESS_PLUGINS, [])
      selected = [p for p in selected if p != plugin_id]
      if via_wg:
        selected.append(plugin_id)

      self._plugin.state.save({const.KEY_WG_EGRESS_PLUGINS: selected})
      route = "WireGuard" if via_wg else "default interface"
      self._plugin.logger.info(f"{plugin_id} outbound traffic: {route}")

      return {"status": "ok", "data": {"plugin": plugin_id, "via_wg": via_wg}}
    except Exception as e:
      self._plugin.logger.error(f"Error in wg_set_routing: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
