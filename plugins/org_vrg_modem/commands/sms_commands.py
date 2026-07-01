from plugins.org_vrg_modem.plugin import ModemPlugin
from sdk.gateway import Gateway, GatewayCommand


class CommandSmsCommands(GatewayCommand):
  _plugin: ModemPlugin

  def __init__(self, plugin: ModemPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, gateway: Gateway, payload, args):
    await gateway.send_text(
      payload=payload,
      text="SMS commands",
      keyboard=[
        [{"text": "List SMS", "callback_data": "command__modem__list_sms"}],
      ],
    )
