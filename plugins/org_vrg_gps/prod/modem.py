import json
import re
from datetime import UTC, datetime
from logging import Logger

from plugins.org_vrg_gps.modem import Modem
from sdk.helper import return_subprocess


class ModemImpl(Modem):
  _logger: Logger
  _modem_id: str = None

  @property
  def modem_id(self) -> str:
    return self._modem_id

  def __init__(self, logger: Logger):
    self._logger = logger

  def is_enabled(self) -> bool:
    return True if self._modem_id else False

  async def enable(self) -> bool:
    # Check 1: ModemManager is running
    result = await return_subprocess(cmd=["systemctl", "is-active", "ModemManager"])
    if result.returncode != 0:
      self._logger.warning("ModemManager is not running")
      self._modem_id = None
      return False

    # Check 2: Modem is present
    result = await return_subprocess(cmd=["mmcli", "-L"])
    if result.returncode != 0 or "Modem" not in result.stdout:
      self._logger.warning("Modem not found")
      self._modem_id = None
      return False

    # Get modem ID (first found)
    match = re.search(r"/Modem/(\d+)", result.stdout)
    if not match:
      self._logger.warning("Failed to determine modem ID")
      self._modem_id = None
      return False

    modem_id = match.group(1)

    # Check 3: Modem supports gps-nmea
    result = await return_subprocess(cmd=["mmcli", "-m", modem_id, "--location-status"])
    if result.returncode != 0:
      self._logger.warning(f"Failed to get location info for modem {modem_id}")
      self._modem_id = None
      return False

    caps_line = next((l for l in result.stdout.splitlines() if "capabilities:" in l), "")
    if "gps-nmea" not in caps_line:
      self._logger.warning(
        f"Modem {modem_id} does not support gps-nmea. Available: {caps_line.strip()}"
      )
      self._modem_id = None
      return False

    self._modem_id = modem_id
    return True

  async def enable_gps(self) -> bool:
    if not self._modem_id:
      raise Exception("Modem not enabled!")

    try:
      result = await return_subprocess(
        cmd=[
          "mmcli",
          "-m",
          self._modem_id,
          "--location-enable-gps-nmea",
          "--location-enable-gps-raw",
          "--location-enable-agps-msa",
        ]
      )

      if result.returncode != 0:
        self._logger.warning(result.stderr)
        return False

      return True

    except Exception as e:
      self._logger.warning(f"enable gps error: {e}")
      return False

  @staticmethod
  def _parse_gps_datetime(utc_str: str, gprmc: str | None) -> datetime | None:
    """
    Assembles datetime from two mmcli sources:
    - utc_str: UTC time in "HH:MM:SS.S" format (from gps.utc)
    - gprmc: $GPRMC sentence, date in field 9 (DDMMYY)
    Returns datetime in device local TZ or None.
    """
    if not utc_str or utc_str == "--":
      return None

    if not gprmc:
      return None

    fields = gprmc.split(",")
    if len(fields) <= 9:
      return None

    date_str = fields[9]  # DDMMYY
    if not date_str or len(date_str) != 6:
      return None

    try:
      day = int(date_str[0:2])
      month = int(date_str[2:4])
      year = 2000 + int(date_str[4:6])

      # mmcli returns time as "HH:MM:SS.S" — strip colons and fractional seconds
      time_digits = utc_str.replace(":", "").split(".")[0]  # → "HHMMSS"
      hour = int(time_digits[0:2])
      minute = int(time_digits[2:4])
      second = int(time_digits[4:6])

      dt_utc = datetime(year, month, day, hour, minute, second, tzinfo=UTC)
      return dt_utc.astimezone()  # convert to device local TZ
    except (ValueError, IndexError):
      return None

  async def get_location_gps(self) -> dict:
    if not self._modem_id:
      raise Exception("Modem not enabled!")

    result = await return_subprocess(
      cmd=["mmcli", "-m", self._modem_id, "--location-get", "--output-json"]
    )

    try:
      data = json.loads(result.stdout)
      modem = data.get("modem")
      location = modem.get("location")
      gps = location.get("gps")

      nmea = gps.get("nmea") or []
      gprmc = next((s for s in nmea if isinstance(s, str) and s.startswith("$GPRMC")), None)

      dt = self._parse_gps_datetime(gps.get("utc"), gprmc)

      speed_kmh = None
      if gprmc:
        fields = gprmc.split(",")
        if len(fields) > 7 and fields[7]:
          try:
            speed_kmh = round(float(fields[7]) * 1.852, 1)
          except ValueError:
            pass

      return {
        "longitude": gps.get("longitude"),
        "latitude": gps.get("latitude"),
        "datetime": dt.isoformat() if dt else None,
        "speed": speed_kmh,
      }
    except Exception as e:
      self._logger.warning(f"gps parsing error: {e}")
      return None

  async def disable_gps(self) -> bool:
    if not self._modem_id:
      raise Exception("Modem not enabled!")

    try:
      result = await return_subprocess(
        cmd=[
          "mmcli",
          "-m",
          self._modem_id,
          "--location-disable-gps-nmea",
          "--location-disable-gps-raw",
        ]
      )

      if result.returncode != 0:
        self._logger.warning(result.stderr)
        return False

      return True

    except Exception as e:
      self._logger.warning(f"disable gps error: {e}")
      return False

  async def enable_lbs(self) -> bool:
    if not self._modem_id:
      raise Exception("Modem not enabled!")

    try:
      result = await return_subprocess(
        cmd=["mmcli", "-m", self._modem_id, "--command", "AT+CLBS=1,1"]
      )

      if result.returncode != 0:
        self._logger.warning(result.stderr)
        return False

      return True

    except Exception as e:
      self._logger.warning(f"enable lbs error: {e}")
      return False

  async def get_location_lbs(self) -> dict:
    if not self._modem_id:
      raise Exception("Modem not enabled!")

    result = await return_subprocess(
      cmd=["mmcli", "-m", self._modem_id, "--command", "AT+CLBS=4,1"]
    )

    try:
      match = re.search(r"\+CLBS:\s*(\d+),([-\d.]+),([-\d.]+),(\d+)", result.stdout)

      if match:
        error_code = int(match.group(1))
        if error_code == 0:
          return {
            "latitude": float(match.group(2)),
            "longitude": float(match.group(3)),
            "accuracy": int(match.group(4)),
          }
    except Exception as e:
      self._logger.warning(f"gps parsing error: {e}")

    return None
