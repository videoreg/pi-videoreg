from plugins.org_vrg_core.methods.datetime_state import (
  has_timedatectl,
  list_timezones,
  read_datetime_state,
)
from plugins.org_vrg_core.plugin import CorePlugin
from sdk.helper import return_subprocess
from sdk.socket.api import ApiMethod


class MethodSetDatetime(ApiMethod):
  """Set the system timezone and/or date-time.

  Accepts ``{"datetime"?: "YYYY-MM-DDTHH:MM[:SS]", "timezone"?: "Area/City"}``.
  ``timedatectl`` refuses to set the time while NTP is active, so setting a manual
  time disables NTP only for the duration of the ``set-time`` call and restores it
  afterwards — a manual time set must not turn off automatic synchronization. The
  PiSugar RTC is then updated so the clock survives power loss.
  """

  _plugin: CorePlugin

  def __init__(self, plugin: CorePlugin):
    super().__init__()
    self._plugin = plugin

  @staticmethod
  def _normalize_datetime(value: str) -> str | None:
    """Convert a datetime-local value to `YYYY-MM-DD HH:MM:SS`, or None if invalid."""
    value = value.strip().replace("T", " ")
    date_part, _, time_part = value.partition(" ")
    if not date_part or not time_part:
      return None
    if time_part.count(":") == 1:
      time_part += ":00"
    return f"{date_part} {time_part}"

  async def _run(self, cmd: list[str]) -> tuple[bool, str]:
    result = await return_subprocess(cmd)
    if result.returncode != 0:
      return False, (result.stderr.strip() or result.stdout.strip())
    return True, ""

  async def _update_pisugar_rtc(self):
    """Best-effort: mirror the new system time to the PiSugar RTC via its shell script.

    Failures are logged but never abort the request — the board may be absent on
    a non-PiSugar device.
    """
    try:
      iso_result = await return_subprocess(["date", "+%Y-%m-%dT%H:%M:%S%:z"])
      if iso_result.returncode != 0:
        self._plugin.logger.warning("set_datetime: failed to read current ISO time for RTC")
        return
      iso = iso_result.stdout.strip()
      script = str(self._plugin.runner.videoreg.app_path("task/pisugar.sh"))
      rtc_result = await return_subprocess(["bash", script, "set_rtc_time", iso])
      if rtc_result.returncode != 0 or rtc_result.stdout.strip() != "ok":
        self._plugin.logger.warning(
          f"set_datetime: PiSugar RTC update skipped/failed: "
          f"{rtc_result.stdout.strip()} {rtc_result.stderr.strip()}"
        )
    except Exception as e:
      self._plugin.logger.warning(f"set_datetime: PiSugar RTC update error: {e}")

  async def exec(self, args):
    try:
      if not isinstance(args, dict):
        return {"status": "error", "error": "Invalid arguments"}

      timezone = args.get("timezone")
      raw_datetime = args.get("datetime")

      if not timezone and not raw_datetime:
        return {"status": "error", "error": "Nothing to set"}

      if not has_timedatectl():
        return {"status": "error", "error": "timedatectl is not available on this system"}

      if timezone:
        if timezone not in await list_timezones():
          return {"status": "error", "error": f"Unknown timezone: {timezone}"}
        ok, err = await self._run(["sudo", "timedatectl", "set-timezone", timezone])
        if not ok:
          return {"status": "error", "error": err}

      if raw_datetime:
        normalized = self._normalize_datetime(raw_datetime)
        if normalized is None:
          return {"status": "error", "error": f"Invalid datetime: {raw_datetime}"}

        # timedatectl refuses to set the time while NTP is active. Disable it
        # only for this operation and restore it afterwards so a manual time set
        # keeps automatic synchronization enabled (it will re-sync once able).
        ntp_was_on = bool((await read_datetime_state()).get("ntp"))

        if ntp_was_on:
          ok, err = await self._run(["sudo", "timedatectl", "set-ntp", "false"])
          if not ok:
            return {"status": "error", "error": err}

        ok, err = await self._run(["sudo", "timedatectl", "set-time", normalized])

        if ntp_was_on:
          # Restore NTP regardless of whether set-time succeeded.
          restore_ok, restore_err = await self._run(["sudo", "timedatectl", "set-ntp", "true"])
          if ok and not restore_ok:
            return {"status": "error", "error": restore_err}

        if not ok:
          return {"status": "error", "error": err}

        await self._update_pisugar_rtc()

      return {"status": "ok", "data": await read_datetime_state()}
    except Exception as e:
      self._plugin.logger.error(f"Error in set_datetime: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
