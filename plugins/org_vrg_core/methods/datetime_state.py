import os
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import available_timezones

from sdk.helper import return_subprocess

# Last-resort timezone list when neither `timedatectl` nor the `zoneinfo`
# database are available (e.g. a minimal container without tzdata).
_FALLBACK_TIMEZONES = [
  "UTC",
  "Europe/London",
  "Europe/Berlin",
  "Europe/Paris",
  "Europe/Madrid",
  "Europe/Rome",
  "Europe/Helsinki",
  "Europe/Kyiv",
  "Europe/Moscow",
  "Europe/Istanbul",
  "Asia/Dubai",
  "Asia/Yekaterinburg",
  "Asia/Almaty",
  "Asia/Novosibirsk",
  "Asia/Tashkent",
  "Asia/Kolkata",
  "Asia/Bangkok",
  "Asia/Shanghai",
  "Asia/Tokyo",
  "Australia/Sydney",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Sao_Paulo",
]


def has_timedatectl() -> bool:
  """Whether `timedatectl` is available (i.e. system time can be managed)."""
  return shutil.which("timedatectl") is not None


async def _safe_run(cmd):
  """Run a command, returning None if its binary is missing instead of raising."""
  try:
    return await return_subprocess(cmd)
  except FileNotFoundError:
    return None


async def list_timezones() -> list[str]:
  """All timezone names known to the system.

  Prefers `timedatectl list-timezones`, falls back to the Python `zoneinfo`
  database, and finally to a small hardcoded list.
  """
  if has_timedatectl():
    result = await _safe_run(["timedatectl", "list-timezones"])
    if result and result.returncode == 0:
      zones = [line for line in result.stdout.splitlines() if line]
      if zones:
        return zones

  try:
    zones = sorted(available_timezones())
    if zones:
      return zones
  except Exception:
    pass

  return list(_FALLBACK_TIMEZONES)


def _read_system_timezone() -> str:
  """Best-effort system timezone name without `timedatectl`."""
  try:
    tz = Path("/etc/timezone").read_text(encoding="utf-8").strip()
    if tz:
      return tz
  except Exception:
    pass

  try:
    target = os.readlink("/etc/localtime")
    marker = "zoneinfo/"
    if marker in target:
      return target.split(marker, 1)[1]
  except Exception:
    pass

  return os.environ.get("TZ", "")


async def read_datetime_state() -> dict:
  """Current local date/time, timezone and NTP status.

  Reads need no privileges. `supported` reports whether `timedatectl` is present;
  when it is not (e.g. inside a container) the date/time/timezone cannot be
  changed and the timezone/NTP fields are read on a best-effort basis.
  """
  supported = has_timedatectl()
  timezone = ""
  ntp = False
  ntp_synced = False

  if supported:
    result = await _safe_run(
      ["timedatectl", "show", "-p", "Timezone", "-p", "NTP", "-p", "NTPSynchronized", "--value"]
    )
    if result and result.returncode == 0:
      lines = result.stdout.splitlines()
      if len(lines) >= 3:
        timezone = lines[0].strip()
        ntp = lines[1].strip() == "yes"
        ntp_synced = lines[2].strip() == "yes"

  if not timezone:
    timezone = _read_system_timezone()

  return {
    "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    "timezone": timezone,
    "ntp": ntp,
    "ntp_synced": ntp_synced,
    "supported": supported,
    "timezones": await list_timezones(),
  }
