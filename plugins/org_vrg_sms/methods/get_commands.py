from plugins.org_vrg_sms.plugin import SmsPlugin
from sdk.socket.api import ApiMethod


class MethodGetCommands(ApiMethod):
  _plugin: SmsPlugin

  def __init__(self, plugin: SmsPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    return {
      "status": "ok",
      "bot_message": "SMS commands",
      "bot_buttons": [
        [{"text": "List SMS", "callback_data": "button_plugin__sms.list_sms"}],
      ],
    }
