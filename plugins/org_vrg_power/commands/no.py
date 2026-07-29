from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.gateway import Gateway, GatewayCommand


class CommandNo(GatewayCommand):
  """Cancels a scheduled shutdown when `/shutdown` and `/no` arrive in the same batch.

  The cancellation itself happens in the gateway before dispatch (see
  sdk/command_cancel.py), so this handler runs only for a lone `/no` — one that arrived
  without a same-iteration `/shutdown` to cancel. It just reports there was nothing to do.
  """

  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, gateway: Gateway, payload, args):
    await gateway.send_text(payload, self._plugin.runner.i18n.t("power.no.nothing_to_cancel"))
