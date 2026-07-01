from datetime import datetime
from logging import Logger

from plugins.org_vrg_sms.sms import SMS
from plugins.org_vrg_sms.sms_manager import SmsManager
from sdk.at import info as at_info
from sdk.at import sms as at_sms
from sdk.at.transport import AtTransport


class SmsManagerImpl(SmsManager):
  """SMS access over the modem's raw AT port (no ModemManager / dbus).

  Reads incoming messages via AT+CMGL (PDU mode), merges multipart parts into
  whole messages, and deletes every part from the modem after reading. The
  AtTransport is shared with the GPS plugin (same vrg-modem process) — it opens
  the serial port once, serialises access via its internal lock, and self-heals
  on port errors, so this manager never opens or closes it directly.
  """

  def __init__(self, logger: Logger, transport: AtTransport):
    self.logger = logger
    self._transport = transport

  async def read_and_delete_sms(self) -> list[SMS]:
    try:
      messages = await at_sms.list_messages(self._transport)
    except Exception as e:
      self.logger.warning(f"sms read error: {e}")
      return []

    result: list[SMS] = []
    for message in messages:
      timestamp = (
        message.timestamp.isoformat()
        if message.timestamp
        else datetime.now().astimezone().isoformat()
      )
      result.append(SMS(message.number, message.text, timestamp))

      # Delete every part of the message after reading.
      for index in sorted(message.indices, reverse=True):
        try:
          response = await at_sms.delete(self._transport, index)
          if not response.ok:
            self.logger.error(f"sms delete index={index} failed: {response.final}")
        except Exception as e:
          self.logger.error(f"sms delete error index={index}: {e}")

    return result

  async def send_sms(self, number: str, text: str) -> None:
    try:
      pdu_hex, response = await at_sms.send(self._transport, number, text)
    except Exception as e:
      raise RuntimeError(f"send sms error: {e}") from e

    self.logger.debug(f"sent sms pdu: {pdu_hex}")
    if not response.ok:
      raise RuntimeError(f"send sms failed: {response.final}")

  async def get_modem_info(self) -> dict:
    try:
      return await at_info.get_modem_info(self._transport)
    except Exception as e:
      self.logger.warning(f"modem info error: {e}")
      return {"connected": False}
