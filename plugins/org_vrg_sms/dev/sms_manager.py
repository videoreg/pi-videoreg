from plugins.org_vrg_sms.sms_manager import SmsManager


class SmsManagerImpl(SmsManager):
  async def read_and_delete_sms(self):
    return []

  async def send_sms(self, number, text):
    pass
