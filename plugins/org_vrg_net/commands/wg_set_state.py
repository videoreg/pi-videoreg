from plugins.org_vrg_net.plugin import NetPlugin
from sdk.gateway import Gateway, GatewayCommand


class CommandWgSetState(GatewayCommand):
  """Brings the WireGuard gateway up or down immediately from a bot button."""

  _plugin: NetPlugin
  _enable: bool

  def __init__(self, plugin: NetPlugin, enable: bool):
    super().__init__()
    self._plugin = plugin
    self._enable = enable

  async def exec(self, gateway: Gateway, payload, args):
    monitor = self._plugin.wg_monitor

    if self._enable:
      ok = await monitor.start_wireguard()
    else:
      ok = await monitor.stop_wireguard()

    if ok is False:
      action = "start" if self._enable else "stop"
      await gateway.send_text(payload, f"Failed to {action} WireGuard")
      return

    active = await monitor.is_wg_active()
    await gateway.send_text(payload, f"WireGuard active: {active}")
