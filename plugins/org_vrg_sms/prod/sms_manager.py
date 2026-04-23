import asyncio
from functools import wraps
from logging import Logger

import dbus

from plugins.org_vrg_sms.sms import SMS
from plugins.org_vrg_sms.sms_manager import SmsManager


def _async_retry(max_attempts=5, delay=2, backoff=2):
  """
  Async retry decorator

  Args:
      max_attempts: maximum number of attempts
      delay: initial delay in seconds
      backoff: delay multiplier
  """

  def decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
      current_delay = delay
      last_error = None

      for attempt in range(max_attempts):
        try:
          return await func(*args, **kwargs)
        except dbus.DBusException as e:
          if "WrongState" in str(e) or "enabling" in str(e).lower():
            last_error = e
            if attempt < max_attempts - 1:
              # print(f"⏳ Retry in {current_delay}s (attempt {attempt + 1}/{max_attempts})")
              await asyncio.sleep(current_delay)
              current_delay *= backoff
            else:
              # print(f"❌ Failed after {max_attempts} attempts")
              raise
          else:
            # Different error — do not retry
            raise

      # All attempts exhausted
      raise last_error

    return wrapper

  return decorator


class SmsManagerImpl(SmsManager):
  def __init__(self, logger: Logger):
    self.logger = logger

  def _get_modem_messaging(self):
    bus = dbus.SystemBus()
    manager = bus.get_object("org.freedesktop.ModemManager1", "/org/freedesktop/ModemManager1")
    manager_iface = dbus.Interface(manager, "org.freedesktop.DBus.ObjectManager")
    objects = manager_iface.GetManagedObjects()

    for path, interfaces in objects.items():
      if "org.freedesktop.ModemManager1.Modem" in interfaces:
        modem = bus.get_object("org.freedesktop.ModemManager1", path)
        messaging = dbus.Interface(modem, "org.freedesktop.ModemManager1.Modem.Messaging")
        return bus, messaging

    return None, None

  async def read_and_delete_sms(self) -> list[SMS]:
    bus, messaging, sms_paths = await self._list_sms_with_retry()

    if messaging is None:
      return []

    sms_list: list[SMS] = []

    MM_SMS_PDU_TYPE_DELIVER = 1

    for sms_path in sms_paths:
      sms = bus.get_object("org.freedesktop.ModemManager1", sms_path)
      props = dbus.Interface(sms, "org.freedesktop.DBus.Properties")

      pdu_type = props.Get("org.freedesktop.ModemManager1.Sms", "PduType")

      if int(pdu_type) != MM_SMS_PDU_TYPE_DELIVER:
        continue

      number = props.Get("org.freedesktop.ModemManager1.Sms", "Number")
      text = props.Get("org.freedesktop.ModemManager1.Sms", "Text")
      timestamp = props.Get("org.freedesktop.ModemManager1.Sms", "Timestamp")

      sms_list.append(SMS(str(number), str(text), str(timestamp)))

      try:
        messaging.Delete(sms_path)
      except dbus.DBusException as e:
        self.logger.error(f"sms delete error: {e}")

    return sms_list

  @_async_retry(max_attempts=10, delay=2, backoff=1.5)
  async def _list_sms_with_retry(self):
    bus = dbus.SystemBus()
    manager = bus.get_object("org.freedesktop.ModemManager1", "/org/freedesktop/ModemManager1")
    manager_iface = dbus.Interface(manager, "org.freedesktop.DBus.ObjectManager")
    objects = manager_iface.GetManagedObjects()

    for path, interfaces in objects.items():
      if "org.freedesktop.ModemManager1.Modem" in interfaces:
        modem = bus.get_object("org.freedesktop.ModemManager1", path)
        messaging = dbus.Interface(modem, "org.freedesktop.ModemManager1.Modem.Messaging")
        sms_paths = messaging.List()  # may raise WrongState — retry in that case
        return bus, messaging, sms_paths

    return None, None, []

  async def send_sms(self, number: str, text: str) -> None:
    bus, messaging = self._get_modem_messaging()

    if messaging is None:
      raise RuntimeError("No modem found")

    sms_path = messaging.Create(
      {
        "number": dbus.String(number),
        "text": dbus.String(text),
      }
    )

    sms = bus.get_object("org.freedesktop.ModemManager1", sms_path)
    sms_iface = dbus.Interface(sms, "org.freedesktop.ModemManager1.Sms")

    try:
      sms_iface.Send()
    except Exception as e:
      self.logger.error(f"Send sms error: {e}")
    finally:
      messaging.Delete(sms_path)
