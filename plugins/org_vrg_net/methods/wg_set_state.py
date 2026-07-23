from plugins.org_vrg_net.plugin import NetPlugin
from sdk.socket.api import ApiMethod


class MethodWgSetState(ApiMethod):
  """Brings the WireGuard interface up or down immediately (the "State" switch).

  Unlike auto-connect, this does not persist any preference — it only applies the
  requested state right now via wg-quick.
  """

  _plugin: NetPlugin

  def __init__(self, plugin: NetPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    enable = bool(args.get("enabled")) if isinstance(args, dict) else args == "enable"

    monitor = self._plugin.wg_monitor

    if enable:
      ok = await monitor.start_wireguard()
    else:
      ok = await monitor.stop_wireguard()

    if ok is False:
      action = "start" if enable else "stop"
      return {"status": "error", "error": f"Failed to {action} WireGuard"}

    active = await monitor.is_wg_active()

    return {"status": "ok", "data": {"active": active}}
