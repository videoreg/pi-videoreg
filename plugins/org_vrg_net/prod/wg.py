import asyncio
import os
import subprocess
import time
from logging import Logger

import dbus

import plugins.org_vrg_net.const as const
from plugins.org_vrg_net.wg import Config, WireguardMonitor

# Safety net for routing changes made outside of the monitor; its own up/down drops the cache
ROUTING_INFO_TTL = 60


class WireguardMonitorImpl(WireguardMonitor):
  _logger: Logger
  _config: Config
  _stop_event: asyncio.Event = None

  def __init__(self, logger: Logger, config: Config):
    self._logger = logger
    self._config = config

    # Serializes bringing the interface up / down: the monitor loop, the UI switch, bot
    # commands and the restart after a config change may race otherwise
    self._lock = asyncio.Lock()

    # get_routing_info(cached=True) result. Plugins ask for it on their connections (via
    # net.wg_egress), so it is not re-read from the kernel each time; dropped whenever the
    # interface goes up or down
    self._routing_info = None
    self._routing_info_expires_at = 0

    # Store the last state to prevent duplicate actions
    self.last_state = {"wifi": False, "modem": False, "wg_active": False}

    # Whether to keep WireGuard down while the "wifi" client connection is active.
    # Updated at runtime from the plugin state (KEY_WG_SKIP_ON_WIFI).
    self.skip_on_wifi = True

    self._logger.debug("NetworkMonitor initialized")

  def get_active_connections(self):
    """Gets the list of active connections"""
    try:
      self.bus = dbus.SystemBus()
      self.nm = self.bus.get_object(
        "org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager"
      )
      self.nm_interface = dbus.Interface(self.nm, "org.freedesktop.NetworkManager")

      active_connections = self.nm_interface.Get(
        "org.freedesktop.NetworkManager",
        "ActiveConnections",
        dbus_interface="org.freedesktop.DBus.Properties",
      )

      connections = []
      for conn_path in active_connections:
        try:
          # Check whether the object exists
          conn = self.bus.get_object("org.freedesktop.NetworkManager", conn_path)

          # Get all properties in a single call (atomically)
          props_interface = dbus.Interface(conn, "org.freedesktop.DBus.Properties")

          props = props_interface.GetAll("org.freedesktop.NetworkManager.Connection.Active")

          # State: 2 = activated
          state = props.get("State", 0)
          if state == 2:
            conn_id = str(props.get("Id", ""))

            if conn_id:
              connections.append(conn_id)
              # self._logger.debug(f"Active connection: {conn_id} (type: {conn_type})")

        except dbus.exceptions.DBusException as e:
          error_str = str(e)
          # These errors are expected — the connection has disappeared
          if any(x in error_str for x in ["UnknownMethod", "does not exist", "UnknownObject"]):
            self._logger.debug(f"Connection vanished during enumeration: {conn_path}")
          else:
            self._logger.warning(f"D-Bus error reading connection {conn_path}: {e}")
          continue

        except Exception as e:
          self._logger.warning(f"Unexpected error reading connection {conn_path}: {e}")
          continue

      self._logger.debug(f"Found {len(connections)} active connection(s): {connections}")
      return connections

    except dbus.exceptions.DBusException as e:
      self._logger.error(f"D-Bus error getting active connections: {e}")
      return []
    except Exception as e:
      self._logger.error(f"Error getting active connections: {e}")
      return []

  def is_wifi_connected(self, connections: list):
    """Checks whether WiFi is connected"""
    return self._config.connection_name_wifi in connections

  def is_modem_active(self, connections: list):
    """Checks whether the modem is active"""
    return self._config.connection_name_modem in connections

  def is_wg_configured(self):
    """Checks whether WireGuard is configured"""
    try:
      # Check config existence
      # result = subprocess.run(
      #   ['test', '-f', self._config.wg_config_path],
      #   capture_output=True
      # )
      # if result.returncode != 0:
      #   return False

      # Validate via wg-quick
      result = subprocess.run(
        ["sudo", "wg-quick", "strip", self._config.wg_interface], capture_output=True, text=True
      )
      if result.returncode != 0:
        self._logger.error(
          f"wg-quick strip failed (code {result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
        )
      return result.returncode == 0
    except Exception as e:
      self._logger.error(f"Error checking WireGuard config: {e}")
      return False

  async def is_wg_active(self):
    """Checks whether WireGuard is running (async)"""
    proc = await asyncio.create_subprocess_exec(
      "ip",
      "link",
      "show",
      self._config.wg_interface,
      stdout=asyncio.subprocess.DEVNULL,
      stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    return proc.returncode == 0

  async def _wg_quick(self, action: str, target: str) -> bool:
    proc = await asyncio.create_subprocess_exec(
      "sudo",
      "wg-quick",
      action,
      target,
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
      error_msg = stderr.decode() if stderr else "Unknown error"
      self._logger.error(f"wg-quick {action} failed: {error_msg}")
      return False
    return True

  async def _run(self, *cmd: str) -> str:
    """Runs a command and returns its stdout (empty on failure)"""
    proc = await asyncio.create_subprocess_exec(
      *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
    )
    stdout, _ = await proc.communicate()
    return stdout.decode() if proc.returncode == 0 else ""

  async def _start(self) -> bool:
    self._logger.info("Starting WireGuard...")
    self._routing_info = None

    if await self._wg_quick("up", self._config.wg_interface):
      self._logger.info("WireGuard started successfully")
      await self.notify_wg_enabled()
      return True
    return False

  async def _stop(self) -> bool:
    self._logger.info("Stopping WireGuard...")
    self._routing_info = None

    if await self._wg_quick("down", self._config.wg_interface):
      self._logger.info("WireGuard stopped successfully")
      await self.notify_wg_disabled()
      return True
    return False

  async def start_wireguard(self):
    """Starts WireGuard (async)"""
    async with self._lock:
      return await self._start()

  async def stop_wireguard(self):
    """Stops WireGuard (async)"""
    async with self._lock:
      return await self._stop()

  async def restart_wireguard(self):
    async with self._lock:
      if await self.is_wg_active():
        await self._stop()
      return await self._start()

  async def get_public_key(self, private_key: str) -> str | None:
    proc = await asyncio.create_subprocess_exec(
      "wg",
      "pubkey",
      stdin=asyncio.subprocess.PIPE,
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await proc.communicate(input=private_key.encode())
    return stdout.decode().strip() if proc.returncode == 0 else None

  async def get_routing_info(self, cached: bool = False) -> dict:
    now = time.monotonic()
    if cached and self._routing_info is not None and now < self._routing_info_expires_at:
      return self._routing_info

    info = {"address": None, "rule": False, "default_route": False}

    table = str(const.WG_ROUTE_TABLE)

    addr_out = await self._run("ip", "-4", "-o", "addr", "show", "dev", self._config.wg_interface)
    for line in addr_out.splitlines():
      # Format: "5: wg0    inet 10.8.0.2/24 scope global wg0 ..."
      parts = line.split()
      if "inet" in parts:
        info["address"] = parts[parts.index("inet") + 1].split("/")[0]
        break

    if info["address"]:
      # Format: "1000:\tfrom 10.8.0.2 lookup 51821"
      rules = await self._run("ip", "-4", "rule", "show", "table", table)
      info["rule"] = f"from {info['address']} " in rules.replace("\t", " ") + " "

      routes = await self._run("ip", "-4", "route", "show", "table", table, "default")
      info["default_route"] = bool(routes.strip())

    self._routing_info = info
    self._routing_info_expires_at = now + ROUTING_INFO_TTL
    return info

  def _parse_wg_show(self, output: str) -> dict:
    """
    Parses the output of the 'wg show' command and extracts key parameters.

    Args:
        output: output of the 'wg show' command

    Returns:
        dict with WireGuard parameters
    """
    result = {"public_key": None, "listening_port": None, "peers": []}

    current_peer = None

    for line in output.split("\n"):
      line = line.strip()
      if not line:
        continue

      # Interface
      if line.startswith("interface:"):
        pass  # already known

      # Public key
      elif line.startswith("public key:"):
        result["public_key"] = line.split(":", 1)[1].strip()

      # Private key (hidden)
      elif line.startswith("private key:"):
        pass

      # Listening port
      elif line.startswith("listening port:"):
        port_str = line.split(":", 1)[1].strip()
        try:
          result["listening_port"] = int(port_str)
        except ValueError:
          pass

      # Peer
      elif line.startswith("peer:"):
        # Save the previous peer
        if current_peer:
          result["peers"].append(current_peer)

        # Create a new peer
        current_peer = {
          "public_key": line.split(":", 1)[1].strip(),
          "endpoint": None,
          "allowed_ips": [],
          "latest_handshake": None,
          "transfer_received": None,
          "transfer_sent": None,
        }

      # Peer parameters
      elif current_peer:
        if line.startswith("endpoint:"):
          current_peer["endpoint"] = line.split(":", 1)[1].strip()

        elif line.startswith("allowed ips:"):
          ips_str = line.split(":", 1)[1].strip()
          current_peer["allowed_ips"] = [ip.strip() for ip in ips_str.split(",")]

        elif line.startswith("latest handshake:"):
          current_peer["latest_handshake"] = line.split(":", 1)[1].strip()

        elif line.startswith("transfer:"):
          # Format: "1.25 MiB received, 456.78 KiB sent"
          transfer_str = line.split(":", 1)[1].strip()
          parts = transfer_str.split(",")
          if len(parts) >= 2:
            received = parts[0].strip().replace(" received", "")
            sent = parts[1].strip().replace(" sent", "")
            current_peer["transfer_received"] = received
            current_peer["transfer_sent"] = sent

    # Don't forget to add the last peer
    if current_peer:
      result["peers"].append(current_peer)

    return result

  async def get_wg_info(self) -> dict:
    """
    Gets information about the WireGuard connection.

    Returns:
        dict with fields:
        - active (bool): whether the interface is active
        - interface (str): interface name
        - ip_address (str): interface IP address or None
        - public_key (str): public key or None
        - listening_port (int): listening port or None
        - peers (list): list of connected peers with their parameters
    """
    info = {
      "active": False,
      "interface": self._config.wg_interface,
      "ip_address": None,
      "public_key": None,
      "listening_port": None,
      "peers": [],
    }

    try:
      # Check interface activity
      info["active"] = await self.is_wg_active()

      if info["active"]:
        # Get information from wg show
        proc = await asyncio.create_subprocess_exec(
          "sudo",
          "wg",
          "show",
          self._config.wg_interface,
          stdout=asyncio.subprocess.PIPE,
          stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
          wg_data = self._parse_wg_show(stdout.decode())
          info.update(wg_data)
        else:
          self._logger.warning(f"Failed to get wg show: {stderr.decode()}")

        # Get the interface IP address
        proc = await asyncio.create_subprocess_exec(
          "ip",
          "-4",
          "addr",
          "show",
          self._config.wg_interface,
          stdout=asyncio.subprocess.PIPE,
          stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
          # Parse the output to extract the IP address
          output = stdout.decode()
          for line in output.split("\n"):
            line = line.strip()
            if line.startswith("inet "):
              # Format: inet 10.0.0.2/24 scope global wg0
              ip_part = line.split()[1]
              info["ip_address"] = ip_part  # Includes the subnet mask
              break
        else:
          self._logger.warning(f"Failed to get IP address: {stderr.decode()}")

    except Exception as e:
      self._logger.error(f"Error getting WireGuard info: {e}", exc_info=True)

    return info

  async def notify_wg_enabled(self):
    pass

  async def notify_wg_disabled(self):
    pass

  async def check_and_manage_wireguard(self):
    """Main WireGuard management logic (async)"""
    # Check the configuration only once at startup
    if not hasattr(self, "_config_checked"):
      if not self.is_wg_configured():
        self._logger.error("WireGuard is not properly configured, monitoring disabled")
        return False
      self._config_checked = True

    # Read the state and act on it under the lock, so a concurrent up/down (UI switch,
    # config save) can't change it in between
    async with self._lock:
      # Get the current state
      connections = self.get_active_connections()
      wifi = self.is_wifi_connected(connections)
      modem = self.is_modem_active(connections)
      wg_active = await self.is_wg_active()

      # Check whether the state has changed
      current_state = {"wifi": wifi, "modem": modem, "wg_active": wg_active}

      if current_state != self.last_state:
        self._logger.info(f"State changed: wifi={wifi}, modem={modem}, wg={wg_active}")
        if current_state["wg_active"] != self.last_state["wg_active"]:
          # Brought up / down from outside (e.g. wg-quick from a shell)
          self._routing_info = None
        self.last_state = current_state

      # Make a decision
      if self.skip_on_wifi and wifi:
        # At home (WiFi client connected) — stop WireGuard
        if wg_active:
          await self._stop()
      else:
        # Away from home (or WiFi is not a reason to skip) — start WireGuard
        if not wg_active:
          await self._start()

    return True

  async def start_monitor_loop(self):
    if self._stop_event and not self._stop_event.is_set():
      return

    self._logger.debug("Starting monitor loop...")
    self._stop_event = asyncio.Event()

    while not self._stop_event.is_set():
      try:
        await self.check_and_manage_wireguard()
      except Exception as e:
        self._logger.error(f"Error in monitor loop: {e}", exc_info=True)
      finally:
        await asyncio.sleep(self._config.check_interval)

    self._logger.debug("Monitor loop stopped...")

  def stop_monitor_loop(self):
    if self._stop_event:
      self._stop_event.set()
