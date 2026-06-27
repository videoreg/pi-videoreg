from plugins.org_vrg_sms.plugin import SmsPlugin
from plugins.org_vrg_sms.sms_keyboard import get_sms_keyboard
from sdk.gateway import Gateway, GatewayCommand


class CommandListSms(GatewayCommand):
  _plugin: SmsPlugin

  def __init__(self, plugin: SmsPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, gateway: Gateway, payload, args):
    page = 1
    try:
      page = int(args)
    except:
      pass

    per_page = gateway.list_page_size or 6
    keyboard_data = await get_sms_keyboard(
      videoreg=self._plugin.runner.videoreg, logger=self._plugin.logger, page=page, per_page=per_page
    )

    if keyboard_data.count_total == 0:
      await gateway.send_text(payload=payload, text="There are no SMS")
      return

    await gateway.send_text(
      payload=payload,
      text=f"Page {keyboard_data.page} of {keyboard_data.count_pages}",
      keyboard=keyboard_data.buttons,
    )
