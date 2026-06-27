import asyncio
from datetime import datetime
from logging import Logger

from plugins.org_vrg_sms.sms import SMS
from plugins.org_vrg_sms.sms_manager import SmsManager
from sdk.at import sms as at_sms
from sdk.at.transport import AtTransport

DEFAULT_DEVICE = "/dev/ttyUSB2"


class SmsManagerImpl(SmsManager):
  """SMS access over the modem's raw AT port (no ModemManager / dbus).

  Reads incoming messages via AT+CMGL (PDU mode), merges multipart parts into
  whole messages, and deletes every part from the modem after reading. A single
  AtTransport is kept open and reused; its internal lock serialises reads and
  sends on the shared serial port.
  """

  def __init__(self, logger: Logger, device: str = DEFAULT_DEVICE, baudrate: int = 115200):
    self.logger = logger
    self._device = device
    self._baudrate = baudrate
    self._transport: AtTransport | None = None
    self._open_lock = asyncio.Lock()

  async def _get_transport(self) -> AtTransport:
    if self._transport is None:
      async with self._open_lock:
        if self._transport is None:
          transport = AtTransport(self._device, self._baudrate, self.logger)
          await transport.open()
          self._transport = transport
    return self._transport

  async def _reset(self) -> None:
    """Drop the transport so the next call reopens the port (e.g. after USB re-enumeration)."""
    if self._transport is not None:
      try:
        await self._transport.close()
      except Exception as e:
        self.logger.debug(f"transport close error: {e}")
      self._transport = None

  async def read_and_delete_sms(self) -> list[SMS]:
    try:
      transport = await self._get_transport()
      messages = await at_sms.list_messages(transport)
    except Exception as e:
      self.logger.warning(f"sms read error: {e}")
      await self._reset()
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
          response = await at_sms.delete(transport, index)
          if not response.ok:
            self.logger.error(f"sms delete index={index} failed: {response.final}")
        except Exception as e:
          self.logger.error(f"sms delete error index={index}: {e}")

    return result

  async def send_sms(self, number: str, text: str) -> None:
    try:
      transport = await self._get_transport()
      pdu_hex, response = await at_sms.send(transport, number, text)
    except Exception as e:
      await self._reset()
      raise RuntimeError(f"send sms error: {e}") from e

    self.logger.debug(f"sent sms pdu: {pdu_hex}")
    if not response.ok:
      raise RuntimeError(f"send sms failed: {response.final}")
