from dataclasses import dataclass
from datetime import datetime
from math import atan2, cos, radians, sin, sqrt
from typing import Any

FOOTER = """
    </trkseg>
  </trk>
</gpx>
"""


@dataclass
class Trackpoint:
  lat: Any
  lon: Any
  date: str
  speed: float | None = None  # km/h


class GpsTracker:
  _file_path: str
  _started = False
  _has_points = False
  _min_distance: int
  _last_meaningfull_trackpoint: Trackpoint = None
  _last_trackpoint: Trackpoint = None

  def __init__(self, file_path: str, min_distance: int = 30):
    self._file_path = file_path
    self._min_distance = min_distance

  def start(self):
    if self._started:
      raise Exception("Tracker is already started")

    self._started = True

    with open(self._file_path, "w") as file:
      file.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.0">
  <metadata>
    <name>Videoreg track</name>
    <time>{datetime.now().astimezone().isoformat()}</time>
  </metadata>
  <trk>
    <name>Track 1</name>
    <trkseg>
{FOOTER}""")

  def track(self, lat, lon, speed: float | None = None):
    trackpoint = Trackpoint(lat, lon, datetime.now().astimezone().isoformat(), speed)

    self._last_trackpoint = trackpoint

    if self._last_meaningfull_trackpoint:
      distance = haversine(
        self._last_meaningfull_trackpoint.lat,
        self._last_meaningfull_trackpoint.lon,
        trackpoint.lat,
        trackpoint.lon,
      )

      if distance < self._min_distance:
        return

    self._last_meaningfull_trackpoint = trackpoint

    self._write_trackpoint()

  def _write_trackpoint(self):
    trackpoint = self._last_trackpoint

    if not trackpoint:
      return

    # Open file in read+write mode
    with open(self._file_path, "r+") as file:
      # Seek to end of file
      file.seek(0, 2)  # 2 = SEEK_END

      # Rewind by FOOTER length
      footer_length = len(FOOTER)
      file.seek(file.tell() - footer_length)

      # Write new trackpoint
      speed_xml = (
        f"\n          <speed>{trackpoint.speed}</speed>" if trackpoint.speed is not None else ""
      )
      file.write(f"""
        <trkpt lat="{trackpoint.lat}" lon="{trackpoint.lon}">
          <time>{trackpoint.date}</time>{speed_xml}
        </trkpt>""")

      # Write FOOTER back
      file.write(FOOTER)

    self._has_points = True
    self._last_trackpoint = None

  def close(self) -> bool:
    """Closes the tracker. Returns True if file was kept, False if deleted (no points recorded)."""
    # Write the last point regardless of distance to produce a complete track
    if self._last_trackpoint:
      self._write_trackpoint()

    # if not self._has_points:
    #   os.remove(self._file_path)
    #   return False
    return True


def haversine(lat1, lon1, lat2, lon2):
  """Returns distance in meters between two points on Earth given their lat/lon."""
  R = 6371000  # Earth radius in meters

  lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

  dlat = lat2 - lat1
  dlon = lon2 - lon1

  a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
  c = 2 * atan2(sqrt(a), sqrt(1 - a))

  return R * c
