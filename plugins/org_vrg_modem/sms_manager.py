from plugins.org_vrg_modem.sms import SMS


class SmsManager:
  async def read_and_delete_sms(self) -> list[SMS]:
    raise NotImplementedError()

  async def send_sms(self, number: str, text: str) -> None:
    raise NotImplementedError()

  async def get_modem_info(self) -> dict:
    raise NotImplementedError()
