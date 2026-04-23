from plugins.org_vrg_sms.plugin import SmsPlugin
from sdk.interface import Interface, InterfaceCommand


class CommandGetCommands(InterfaceCommand):
  _plugin: SmsPlugin

  def __init__(self, plugin: SmsPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, interface: Interface, payload, args):
    await interface.send_text(
      payload=payload,
      text="SMS commands",
      keyboard=[
        [{"text": "List SMS", "callback_data": "command__sms__list_sms"}],
      ],
    )
