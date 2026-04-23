import json
from datetime import datetime

from plugins.org_vrg_sms.plugin import SmsPlugin
from plugins.org_vrg_sms.sms import SMS
from sdk.interface import Interface, InterfaceCommand


class CommandGetSms(InterfaceCommand):
  _plugin: SmsPlugin

  def __init__(self, plugin: SmsPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, interface: Interface, payload, args):
    sms_file_name = str(args)

    if not sms_file_name:
      self._plugin.logger.warning(f"Command CommandGetSms: missing sms file name args={args}")
      return

    sms_file_path = self._plugin.runner.videoreg.sms_path(f"{sms_file_name}.json")

    if not sms_file_path.exists():
      self._plugin.logger.warning(
        f"Command CommandGetSms: sms file not found sms_file_name={sms_file_name}"
      )
      return

    try:
      with open(sms_file_path) as f:
        sms_json = json.load(f)

      sms = SMS(**sms_json)

      sms_datetime = datetime.fromisoformat(sms.timestamp)
      sms_datetime_str_for_bot = sms_datetime.strftime("%Y-%m-%d %H:%M:%S")

      await interface.send_text(
        payload=payload,
        text=f"SMS\n\n{sms_datetime_str_for_bot}\n\nFrom: {sms.number}\n\n{sms.text}\n",
      )

    except Exception as e:
      self._plugin.logger.warning(f"Command CommandGetSms error: {e}")
