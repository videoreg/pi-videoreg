import netifaces

# Candidate names of the modem interface, in probing order. The name depends on
# the mode the modem runs in: MBIM/QMI enumerates as wwan0, RNDIS/ECM as usb0,
# and a dial-up fallback as ppp0. Hardcoding wwan0 reports no modem address at
# all on devices where the modem came up as usb0.
MODEM_INTERFACES = ["wwan0", "usb0", "ppp0"]


def get_current_ip():
  # Priority order of interfaces: wg0 > wlan0 > modem > 0.0.0.0
  interfaces = ["wg0", "wlan0"]
  ip = None

  for interface in interfaces:
    try:
      ip = get_interface_ip(interface)
      if ip:
        break
    except:
      pass

  if not ip:
    ip = get_modem_ip()

  if not ip:
    ip = "0.0.0.0"

  return ip


def get_modem_ip() -> str:
  """Returns the address of whichever modem interface currently has one."""
  interface = get_modem_interface()

  return get_interface_ip(interface) if interface else None


def get_modem_interface() -> str:
  """Returns the name of the modem interface that currently has an address."""
  for interface in MODEM_INTERFACES:
    try:
      if get_interface_ip(interface):
        return interface
    except Exception:
      pass

  return None


def get_interface_ip(interface: str) -> str:
  ifaddresses = netifaces.ifaddresses(interface)

  if not ifaddresses or netifaces.AF_INET not in ifaddresses:
    return None

  addresses = ifaddresses.get(netifaces.AF_INET)

  if not addresses or not isinstance(addresses, list) or len(addresses) < 1:
    return None

  address = addresses[0]

  if not address or "addr" not in address:
    return None

  return address.get("addr")
