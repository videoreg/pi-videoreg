from datetime import datetime, timedelta

from plugins.org_vrg_core.plugin import CorePlugin
from sdk.socket.api import ApiMethod

TRIP_EVENTS = {"charging_on", "charging_off"}


class MethodGetTripState(ApiMethod):
  _plugin: CorePlugin

  def __init__(self, plugin: CorePlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      journal_dir = self._plugin.runner.videoreg.private_path(
        f"data/plugins/{self._plugin.id}/journal"
      )

      if not journal_dir.exists():
        return {"status": "ok", "data": {"state": None, "start": None}}

      today = datetime.now().date()
      yesterday = today - timedelta(days=1)
      candidate_dates = [today, yesterday]

      last_event = None

      for date in candidate_dates:
        date_str = date.strftime("%Y-%m-%d")
        journal_file = journal_dir / f"{date_str}.txt"

        if not journal_file.exists():
          continue

        with open(journal_file, "r", encoding="utf-8") as f:
          lines = f.readlines()

        for line in reversed(lines):
          line = line.strip()
          if not line:
            continue
          parts = line.split(",", 3)
          if len(parts) < 3:
            continue
          event_type = parts[2]
          if event_type in TRIP_EVENTS:
            last_event = {"at": parts[0], "type": event_type}
            break

        if last_event is not None:
          break

      if last_event is None:
        return {"status": "ok", "data": {"state": None, "start": None}}

      if last_event["type"] == "charging_on":
        state = "in_trip"
      else:
        state = "parked"

      return {"status": "ok", "data": {"state": state, "start": last_event["at"]}}

    except Exception as e:
      self._plugin.logger.error(f"Error in get_trip_state: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
