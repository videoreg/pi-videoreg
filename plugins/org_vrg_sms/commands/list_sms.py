from plugins.org_vrg_sms.plugin import SmsPlugin
from plugins.org_vrg_sms.sms_keyboard import get_sms_keyboard
from sdk.interface import Interface, InterfaceCommand


class CommandListSms(InterfaceCommand):
  _plugin: SmsPlugin

  def __init__(self, plugin: SmsPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, interface: Interface, payload, args):
    page = 1
    try:
      page = int(args)
    except:
      pass

    keyboard_data = await get_sms_keyboard(
      videoreg=self._plugin.runner.videoreg, logger=self._plugin.logger, page=page
    )

    if keyboard_data.count_total == 0:
      await interface.send_text(payload=payload, text="There are no SMS")
      return

    await interface.send_text(
      payload=payload,
      text=f"Page {keyboard_data.page} of {keyboard_data.count_pages}",
      keyboard=keyboard_data.buttons,
    )
