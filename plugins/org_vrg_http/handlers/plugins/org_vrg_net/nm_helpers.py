"""Common helpers for working with NetworkManager"""

import asyncio


async def get_connection_info(connection_name: str, logger, properties_map: dict = None):
  """
  Get NetworkManager connection info

  Args:
    connection_name: Connection name in NetworkManager
    logger: Logger for output
    properties_map: Mapping of nmcli properties to response keys
                   Format: {'nmcli_property': 'response_key'}
                   Example: {'802-11-wireless.ssid': 'ssid', 'gsm.apn': 'apn'}

  Returns:
    dict: Connection info with keys:
      - enabled: bool - whether the connection is active
      - autoconnect: bool - autoconnect setting
      - ip: str - IP address (if connection is active)
      - device: str - device (if connection is active)
      - Additional properties from properties_map
  """
  info = {"enabled": False, "autoconnect": False, "ip": "", "device": ""}

  # Add default values for properties from properties_map
  if properties_map:
    for response_key in properties_map.values():
      info[response_key] = ""

  try:
    # Check if the connection exists
    process = await asyncio.create_subprocess_exec(
      "nmcli",
      "connection",
      "show",
      connection_name,
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
      logger.warning(f"Connection '{connection_name}' not found or not accessible")
      return info

    output = stdout.decode("utf-8")

    # Parse nmcli output
    for line in output.split("\n"):
      if ":" not in line:
        continue

      key, value = line.split(":", 1)
      key = key.strip()
      value = value.strip()

      # Check connection status
      if key == "GENERAL.STATE":
        # "activated" means the connection is active
        info["enabled"] = "activated" in value.lower()

      # Autoconnect
      elif key == "connection.autoconnect":
        info["autoconnect"] = value.lower() in ["yes", "true", "1"]

      # Device
      elif key == "GENERAL.DEVICES":
        info["device"] = value if value and value != "--" else ""

      # Custom properties from properties_map
      elif properties_map and key in properties_map:
        response_key = properties_map[key]
        info[response_key] = value if value and value != "--" else ""

    # If connection is active, get the IP address
    if info["enabled"] and info["device"]:
      ip = await get_device_ip(info["device"], logger)
      info["ip"] = ip

  except Exception as e:
    logger.error(f"Error getting connection info for '{connection_name}': {e}")

  return info


async def get_device_ip(device: str, logger):
  """Get the IP address of a device"""
  try:
    process = await asyncio.create_subprocess_exec(
      "nmcli",
      "-g",
      "IP4.ADDRESS",
      "device",
      "show",
      device,
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
      return ""

    ip_with_mask = stdout.decode("utf-8").strip()

    # Strip subnet mask (e.g. 192.168.1.1/24 -> 192.168.1.1)
    if ip_with_mask and "/" in ip_with_mask:
      ip = ip_with_mask.split("/")[0]
      return ip

    return ip_with_mask if ip_with_mask and ip_with_mask != "--" else ""

  except Exception as e:
    logger.error(f"Error getting IP for device '{device}': {e}")
    return ""


async def set_connection_property(connection_name: str, property_name: str, value: str, logger):
  """Set a connection property via nmcli"""
  process = await asyncio.create_subprocess_exec(
    "nmcli",
    "connection",
    "modify",
    connection_name,
    property_name,
    value,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
  )

  stdout, stderr = await process.communicate()

  if process.returncode != 0:
    error_msg = stderr.decode("utf-8").strip()
    logger.error(f"Failed to set {property_name} for {connection_name}: {error_msg}")
    raise Exception(f"Failed to set {property_name}: {error_msg}")

  logger.info(f"Set {property_name}={value} for {connection_name}")


async def connection_up(connection_name: str, logger):
  """Bring a connection up"""
  process = await asyncio.create_subprocess_exec(
    "nmcli",
    "connection",
    "up",
    connection_name,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
  )

  stdout, stderr = await process.communicate()

  if process.returncode != 0:
    error_msg = stderr.decode("utf-8").strip()
    logger.error(f"Failed to activate {connection_name}: {error_msg}")
    raise Exception(f"Failed to activate connection: {error_msg}")

  logger.info(f"Connection {connection_name} activated")


async def connection_down(connection_name: str, logger):
  """Bring a connection down"""
  process = await asyncio.create_subprocess_exec(
    "nmcli",
    "connection",
    "down",
    connection_name,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
  )

  stdout, stderr = await process.communicate()

  if process.returncode != 0:
    error_msg = stderr.decode("utf-8").strip()
    logger.error(f"Failed to deactivate {connection_name}: {error_msg}")
    raise Exception(f"Failed to deactivate connection: {error_msg}")

  logger.info(f"Connection {connection_name} deactivated")
