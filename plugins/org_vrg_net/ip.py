import netifaces


def get_current_ip():
  # Priority order of interfaces: wg0 > wlan0 > wwan0 > 0.0.0.0
  interfaces = ["wg0", "wlan0", "wwan0"]
  ip = None

  for interface in interfaces:
    try:
      ip = get_interface_ip(interface)
      if ip:
        break
    except:
      pass

  if not ip:
    ip = "0.0.0.0"

  return ip


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
