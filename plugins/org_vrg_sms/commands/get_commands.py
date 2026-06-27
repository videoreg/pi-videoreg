from plugins.org_vrg_sms.plugin import SmsPlugin
from sdk.gateway import Gateway, GatewayCommand


class CommandGetCommands(GatewayCommand):
  _plugin: SmsPlugin

  def __init__(self, plugin: SmsPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, gateway: Gateway, payload, args):
    await gateway.send_text(
      payload=payload,
      text="SMS commands",
      keyboard=[
        [{"text": "List SMS", "callback_data": "command__sms__list_sms"}],
      ],
    )
