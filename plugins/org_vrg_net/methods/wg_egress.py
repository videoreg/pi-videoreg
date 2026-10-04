import plugins.org_vrg_net.const as const
from plugins.org_vrg_net.plugin import NetPlugin
from sdk.socket.api import ApiMethod


class MethodWgEgress(ApiMethod):
  """Returns the local address a plugin must bind its outbound sockets to (sdk/egress.py).

  Args: {"plugin": <plugin id>}
  Data: {"address": "10.8.0.2"} when the plugin is routed through WireGuard and the tunnel
  is up and routes the internet; {"address": None} — use the default interface.

  Called periodically by every egress plugin, so it must stay cheap: plugins that are not
  routed through the tunnel get an answer from the state alone, the others from the
  monitor's cached routing info.
  """

  _plugin: NetPlugin

  def __init__(self, plugin: NetPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    plugin_id = args.get("plugin") if isinstance(args, dict) else None

    try:
      if plugin_id not in self._plugin.state.get(const.KEY_WG_EGRESS_PLUGINS, []):
        return {"status": "ok", "data": {"address": None}}

      info = await self._plugin.wg_monitor.get_routing_info(cached=True)
      routed = info["address"] and info["rule"] and info["default_route"]

      return {"status": "ok", "data": {"address": info["address"] if routed else None}}
    except Exception as e:
      self._plugin.logger.error(f"Error in wg_egress: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
