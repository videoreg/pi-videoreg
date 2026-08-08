import json

from plugins.org_vrg_core.plugin import CorePlugin
from sdk.socket.api import ApiMethod

# Events that clear a "beacon absent" state: the beacon returned, or the feature was
# toggled (enabling/disabling stops it from gating trips).
BEACON_CLEARS = {"beacon_found", "beacon_enabled", "beacon_disabled"}


class MethodGetTripState(ApiMethod):
  """Current trip/parking state, derived from the journal exactly like the Trips page.

  A trip is when the vehicle is running. With the BLE-beacon feature external power may
  keep flowing while parked (each RTC wake-up emits charging_on), so power alone does
  not mark a trip: the state is power present AND the beacon not confirmed absent. With
  the feature off there are no beacon events and this degrades to the classic
  power-only (charging_on / charging_off) reading.

  Keep the segmentation here in sync with buildBlocks() in TripsComponent.js.
  """

  _plugin: CorePlugin

  def __init__(self, plugin: CorePlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      events = self._read_events()
      if not events:
        return {"status": "ok", "data": {"state": None, "start": None}}

      segment = self._last_segment(events)
      if segment is None:
        return {"status": "ok", "data": {"state": None, "start": None}}

      kind, start = segment
      state = "in_trip" if kind == "trip" else "parked"
      return {"status": "ok", "data": {"state": state, "start": start}}

    except Exception as e:
      self._plugin.logger.error(f"Error in get_trip_state: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}

  def _read_events(self) -> list[dict]:
    """Parse the two most recent journal files into chronological events."""
    journal_dir = self._plugin.runner.videoreg.private_path(
      f"data/plugins/{self._plugin.id}/journal"
    )
    if not journal_dir.exists():
      return []

    events = []
    for journal_file in sorted(journal_dir.glob("*.txt"))[-2:]:
      with open(journal_file, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
          parts = line.strip().split(",", 3)
          if len(parts) < 4:
            continue
          try:
            data = json.loads(parts[3])
          except ValueError:
            data = None
          events.append({"date": parts[0], "type": parts[2], "data": data})

    events.sort(key=lambda e: e["date"])
    return events

  def _last_segment(self, events: list[dict]) -> tuple[str, str] | None:
    """Return (kind, start) of the segment the device is currently in."""
    real_loss = self._real_losses(events)
    absent_sessions = self._absent_session_starts(events)

    charging = None  # None until the first power event is seen
    beacon_absent = False  # True once the beacon is confirmed gone
    current = None  # (kind, start)

    def apply(date):
      nonlocal current
      if charging is None:
        return  # effective state not yet known
      kind = "trip" if (charging and not beacon_absent) else "parking"
      if current and current[0] == kind:
        return
      current = (kind, date)

    for i, event in enumerate(events):
      # A beacon-absent session marks the beacon gone before its own charging_on is
      # seen, so the wake-up never opens a trip.
      if i in absent_sessions:
        beacon_absent = True
        apply(event["date"])

      event_type = event["type"]
      if event_type == "charging_on":
        charging = True
        apply(event["date"])
      elif event_type == "charging_off":
        charging = False
        apply(event["date"])
      elif event_type in BEACON_CLEARS:
        beacon_absent = False
        apply(event["date"])
      elif event_type == "beacon_lost" and i in real_loss:
        beacon_absent = True
        apply(event["date"])

    return current

  def _real_losses(self, events: list[dict]) -> set[int]:
    """Indices of beacon_lost events that turned out to be real, not transient.

    A loss counts only if a beacon-lost shutdown follows before the beacon returns; a
    flaky beacon that blinks and reappears must not end a trip.
    """
    real_loss = set()
    for i, event in enumerate(events):
      if event["type"] != "beacon_lost":
        continue
      for other in events[i + 1:]:
        if other["type"] in BEACON_CLEARS:
          break  # recovered or feature toggled -> transient
        if other["type"] == "shutdown" and self._is_beacon_lost_shutdown(other):
          real_loss.add(i)  # grace expired -> the loss was real
          break
    return real_loss

  def _absent_session_starts(self, events: list[dict]) -> set[int]:
    """Indices opening a session that was beacon-absent from its very start.

    A beacon already gone when the scanner starts produces no beacon_lost event — the
    presence loop only reports present<->absent transitions and a session begins as
    "absent" — so a parking wake-up leaves nothing but charging_on and a beacon-lost
    shutdown. A session (delimited by core's start events) that ends in a beacon-lost
    shutdown without ever seeing the beacon therefore was a parking wake-up.
    """
    absent_sessions = set()
    session_start = 0
    saw_beacon = False
    ended_beacon_lost = False

    for i in range(len(events) + 1):
      if i == len(events) or events[i]["type"] == "start":
        if ended_beacon_lost and not saw_beacon:
          absent_sessions.add(session_start)
        session_start = i
        saw_beacon = False
        ended_beacon_lost = False
        continue

      event = events[i]
      if event["type"] in BEACON_CLEARS:
        saw_beacon = True
      elif event["type"] == "shutdown":
        ended_beacon_lost = self._is_beacon_lost_shutdown(event)

    return absent_sessions

  @staticmethod
  def _is_beacon_lost_shutdown(event: dict) -> bool:
    data = event.get("data")
    return bool(isinstance(data, dict) and data.get("reason") == "beacon_lost")
