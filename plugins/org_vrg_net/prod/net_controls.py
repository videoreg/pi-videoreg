"""Common functions for working with NetworkManager"""

import asyncio
import subprocess
from logging import Logger

from plugins.org_vrg_net.net_controls import NetControls
from sdk.helper import stream_subprocess
from sdk.videoreg import Videoreg


class NetControlsImpl(NetControls):
  _logger: Logger
  _videoreg: Videoreg

  def __init__(self, logger: Logger, videoreg: Videoreg):
    self._logger = logger
    self._videoreg = videoreg
    pass

  async def get_wifi_radio_status(self):
    """Check WiFi radio status via nmcli"""
    try:
      process = await asyncio.create_subprocess_exec(
        "nmcli", "radio", "wifi", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
      )

      stdout, stderr = await process.communicate()

      if process.returncode != 0:
        self._logger.warning("Failed to get WiFi radio status")
        return True  # Assume enabled by default

      output = stdout.decode("utf-8").strip().lower()
      return output == "enabled"

    except Exception as e:
      self._logger.error(f"Error checking WiFi radio status: {e}")
      return True  # Assume enabled by default

  async def set_connection_enabled(self, name: str, enabled: bool):
    return await stream_subprocess(
      cmd=["bash", str(self._videoreg.app_path("task/wifi.sh")), "up" if enabled else "down", name],
      start_cb=lambda pid, cmd: self._logger.debug(f"CMD (pid={pid}): {cmd}"),
      stdout_cb=lambda pid, s: self._logger.debug(f"STDOUT (pid={pid}): {s}"),
      stderr_cb=lambda pid, s: self._logger.debug(f"STDERR (pid={pid}): {s}"),
    )

  async def set_wifi_blocked(self, blocked: bool):
    return await stream_subprocess(
      cmd=["bash", str(self._videoreg.app_path("task/wifi.sh")), "block" if blocked else "unblock"],
      start_cb=lambda pid, cmd: self._logger.debug(f"CMD (pid={pid}): {cmd}"),
      stdout_cb=lambda pid, s: self._logger.debug(f"STDOUT (pid={pid}): {s}"),
      stderr_cb=lambda pid, s: self._logger.debug(f"STDERR (pid={pid}): {s}"),
    )

  async def get_connection_info(self, connection_name: str, properties_map: dict = None):
    """
    Get information about a NetworkManager connection.

    Args:
      connection_name: Connection name in NetworkManager
      properties_map: Dictionary mapping nmcli properties to response keys.
                    Format: {'nmcli_property': 'response_key'}
                    Example: {'802-11-wireless.ssid': 'ssid', 'gsm.apn': 'apn'}

    Returns:
      dict: Connection information with keys:
        - enabled: bool - whether the connection is active
        - autoconnect: bool - autoconnect flag
        - ip: str - IP address (if the connection is active)
        - device: str - device (if the connection is active)
        - Additional properties from properties_map
    """
    info = {"enabled": False, "autoconnect": False, "ip": "", "device": ""}

    # Add default values for properties from properties_map
    if properties_map:
      for response_key in properties_map.values():
        info[response_key] = ""

    try:
      print("fuck 2")
      # Check whether the connection exists
      process = await asyncio.create_subprocess_exec(
        "sudo",
        "nmcli",
        "connection",
        "show",
        connection_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
      )

      stdout, stderr = await process.communicate()

      if process.returncode != 0:
        self._logger.warning(f"Connection '{connection_name}' not found or not accessible")
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
          # 'activated' means the connection is active
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

      # If the connection is active, get the IP address
      if info["enabled"] and info["device"]:
        ip = await self._get_device_ip(info["device"])
        info["ip"] = ip

    except Exception as e:
      self._logger.error(f"Error getting connection info for '{connection_name}': {e}")

    return info

  async def _get_device_ip(self, device: str):
    """Get the IP address of a device"""
    try:
      print("fuck 3")
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

      # Strip the subnet mask (e.g. 192.168.1.1/24 -> 192.168.1.1)
      if ip_with_mask and "/" in ip_with_mask:
        ip = ip_with_mask.split("/")[0]
        return ip

      return ip_with_mask if ip_with_mask and ip_with_mask != "--" else ""

    except Exception as e:
      self._logger.error(f"Error getting IP for device '{device}': {e}")
      return ""

  async def set_connection_property(self, connection_name: str, property_name: str, value: str):
    """Set a connection property via nmcli"""
    print("fuck 4")
    process = await asyncio.create_subprocess_exec(
      "sudo",
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
      self._logger.error(f"Failed to set {property_name} for {connection_name}: {error_msg}")
      raise Exception(f"Failed to set {property_name}: {error_msg}")

    self._logger.info(f"Set {property_name}={value} for {connection_name}")

  def get_nm_connections(self):
    """Get a list of all NetworkManager connections with IP addresses"""

    print("fuck 5")
    # Get the list of all connections
    result = subprocess.run(
      ["nmcli", "-t", "-f", "NAME,UUID,TYPE,AUTOCONNECT,DEVICE,STATE", "connection", "show"],
      capture_output=True,
      text=True,
    )

    connections = []
    for line in result.stdout.strip().split("\n"):
      if not line:
        continue

      parts = line.split(":")
      conn_name = parts[0]
      conn_uuid = parts[1]
      conn_type = parts[2]
      autoconnect = parts[3]
      device = parts[4] if len(parts) > 3 else ""
      state = parts[5] if len(parts) > 4 else ""

      if conn_name == "lo":
        continue

      print("fuck 6")
      # Get detailed information about the connection
      detail_result = subprocess.run(
        ["nmcli", "-t", "-f", "IP4.ADDRESS,IP6.ADDRESS", "connection", "show", conn_uuid],
        capture_output=True,
        text=True,
      )

      ipv4_addresses = []
      ipv6_addresses = []

      for detail_line in detail_result.stdout.strip().split("\n"):
        if detail_line.startswith("IP4.ADDRESS"):
          ip = detail_line.split(":", 1)[1].strip()
          if ip:
            ipv4_addresses.append(ip)
        elif detail_line.startswith("IP6.ADDRESS"):
          ip = detail_line.split(":", 1)[1].strip()
          if ip:
            ipv6_addresses.append(ip)

      connections.append(
        {
          "id": conn_name.replace(" ", "_").lower(),
          "name": conn_name,
          "uuid": conn_uuid,
          "type": conn_type,
          "autoconnect": autoconnect,
          "device": device,
          "state": state,
          "ipv4": ipv4_addresses,
          "ipv6": ipv6_addresses,
        }
      )

    return connections
