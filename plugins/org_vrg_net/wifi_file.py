"""WiFi provisioning via a plain-text file on the SD card data partition.

Lets the user recover access to the device after entering wrong WiFi settings in the
Web UI: drop `wifi.txt` into the root of the third SD card partition (mounted at
/mnt/data) and reboot. The file holds three lines:

  1. mode: "ap" or "client"
  2. network name (SSID)
  3. password

The settings are applied once on plugin start and the file is deleted afterwards, so
the password does not stay on the card. An invalid file is left in place (and the
reason is logged) so the user can fix it.
"""

import os
import re
from logging import Logger
from pathlib import Path

import plugins.org_vrg_net.const as const
from plugins.org_vrg_net.methods.set_wifi_mode import MethodSetWifiMode
from plugins.org_vrg_net.net_controls import NetControls

# File mode -> NetworkManager profile name.
CONNECTION_NAMES = {
  "ap": const.NM_CONNECTION_AP,
  "client": const.NM_CONNECTION_WIFI,
}


class WifiFileError(Exception):
  pass


class WifiFileSettings:
  mode: str
  ssid: str
  password: str

  def __init__(self, mode: str, ssid: str, password: str):
    self.mode = mode
    self.ssid = ssid
    self.password = password

  @staticmethod
  def parse(text: str) -> "WifiFileSettings":
    lines = [line.strip() for line in text.splitlines()]

    if len(lines) < 3:
      raise WifiFileError("expected 3 lines: mode, network name and password")

    mode, ssid, password = lines[0].lower(), lines[1], lines[2]

    if mode not in CONNECTION_NAMES:
      raise WifiFileError(f'invalid mode "{lines[0]}", must be "ap" or "client"')

    if not 1 <= len(ssid.encode("utf-8")) <= 32:
      raise WifiFileError("network name must be 1 to 32 bytes long")

    # WPA-PSK: an 8..63 character passphrase or a 64-digit hex key.
    if not (8 <= len(password) <= 63 or re.fullmatch(r"[0-9a-fA-F]{64}", password)):
      raise WifiFileError("password must be 8 to 63 characters long")

    return WifiFileSettings(mode, ssid, password)


class WifiFileProvisioner:
  _logger: Logger
  _net_controls: NetControls
  _method_set_wifi_mode: MethodSetWifiMode
  _path: Path

  def __init__(
    self,
    logger: Logger,
    net_controls: NetControls,
    method_set_wifi_mode: MethodSetWifiMode,
    path: Path,
  ):
    self._logger = logger
    self._net_controls = net_controls
    self._method_set_wifi_mode = method_set_wifi_mode
    self._path = path

  async def apply_if_exists(self) -> bool:
    """Apply the settings from the file if it exists. Returns True if applied."""
    if not self._path.is_file():
      return False

    self._logger.info(f"found {self._path}, applying WiFi settings")

    try:
      # utf-8-sig drops the BOM that Windows editors may prepend.
      settings = WifiFileSettings.parse(self._path.read_text(encoding="utf-8-sig"))
    except (WifiFileError, UnicodeDecodeError, OSError) as e:
      self._logger.error(f"invalid {self._path}, settings not applied: {e}")
      return False

    connection = CONNECTION_NAMES[settings.mode]

    try:
      await self._net_controls.set_connection_property(
        connection, "802-11-wireless.ssid", settings.ssid
      )
      await self._net_controls.set_connection_property(
        connection, "802-11-wireless-security.psk", settings.password
      )
    except Exception as e:
      self._logger.error(f"failed to update {connection} from {self._path}: {e}")
      return False

    # The connection may already be active with the old settings, and bringing up an
    # active connection is a no-op, so take it down first to make the new ones apply.
    await self._net_controls.set_connection_enabled(connection, False)

    result = await self._method_set_wifi_mode.exec({"mode": settings.mode})
    if result.get("status") != "ok":
      self._logger.error(f"failed to set WiFi mode from {self._path}: {result.get('error')}")
      return False

    self._logger.info(
      f'WiFi settings applied from {self._path}: mode={settings.mode}, ssid="{settings.ssid}"'
    )

    try:
      os.remove(self._path)
    except OSError as e:
      self._logger.error(f"failed to delete {self._path}: {e}")

    return True
