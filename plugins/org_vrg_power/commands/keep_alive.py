from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.gateway import Gateway, GatewayCommand

REASON = "keep_alive_request"


class CommandKeepAlive(GatewayCommand):
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, gateway: Gateway, payload, args):
    """Keeps the device on for the specified number of minutes.

    Repeated calls extend the timer.
    """
    minutes = int(args) if args else 1
    self._plugin.keep_alive.have_to_wait(REASON, minutes * 60)
    await gateway.send_text(payload, f"Activated for {minutes} min.")
