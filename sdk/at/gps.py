"""GPS parsing for AT-poll location replies.

Pure functions, no I/O. Parses the single-line replies of:

- ``AT+CGPSINFO``  (sim7600 / SIM7xxx) -> ``+CGPSINFO: ...``
- ``AT+CGNSSINFO`` (A7670 / A76xx)     -> ``+CGNSSINFO: ...``

Both report coordinates in NMEA ``ddmm.mmmm`` / ``dddmm.mmmm`` form, which is
converted to signed decimal degrees here. Speed is reported in knots and
converted to km/h. ``date`` (DDMMYY) + ``UTC time`` (HHMMSS.s) are combined
into a timezone-aware datetime in the device's local zone.
"""

from datetime import UTC, datetime

KNOTS_TO_KMH = 1.852


def dm_to_decimal(value: str, hemisphere: str) -> float | None:
  """Convert an NMEA ``[d]ddmm.mmmm`` coordinate to signed decimal degrees.

  The integer part always ends with two minutes digits; everything before
  them is the degrees. Sign is negative for the S / W hemispheres.
  """
  value = value.strip()
  if not value:
    return None
  try:
    int_part = value.split(".")[0]
    if len(int_part) < 3:
      return None
    degrees = int(int_part[:-2])
    minutes = float(value[len(int_part) - 2 :])
    decimal = degrees + minutes / 60.0
    if hemisphere.upper() in ("S", "W"):
      decimal = -decimal
    return round(decimal, 6)
  except (ValueError, IndexError):
    return None


def _parse_datetime(date_str: str, time_str: str) -> datetime | None:
  """Combine DDMMYY + HHMMSS(.s) (UTC) into a local-tz datetime."""
  date_str = date_str.strip()
  time_str = time_str.strip()
  if len(date_str) != 6 or len(time_str) < 6:
    return None
  try:
    day = int(date_str[0:2])
    month = int(date_str[2:4])
    year = 2000 + int(date_str[4:6])
    digits = time_str.split(".")[0]
    hour = int(digits[0:2])
    minute = int(digits[2:4])
    second = int(digits[4:6])
    return datetime(year, month, day, hour, minute, second, tzinfo=UTC).astimezone()
  except (ValueError, IndexError):
    return None


def _knots_to_kmh(value: str) -> float | None:
  value = value.strip()
  if not value:
    return None
  try:
    return round(float(value) * KNOTS_TO_KMH, 1)
  except ValueError:
    return None


def _float_or_none(value: str) -> float | None:
  value = value.strip()
  if not value:
    return None
  try:
    return float(value)
  except ValueError:
    return None


def _strip_prefix(line: str, prefix: str) -> str:
  line = line.strip()
  if line.upper().startswith(prefix):
    line = line[len(prefix) :]
  return line.strip()


def _build(lat, ns, lon, ew, date, utc, alt, speed, course) -> dict | None:
  latitude = dm_to_decimal(lat, ns)
  longitude = dm_to_decimal(lon, ew)
  if latitude is None or longitude is None:
    return None
  dt = _parse_datetime(date, utc)
  return {
    "latitude": latitude,
    "longitude": longitude,
    "datetime": dt.isoformat() if dt else None,
    "altitude": _float_or_none(alt),
    "speed": _knots_to_kmh(speed),
    "course": _float_or_none(course),
  }


def parse_cgpsinfo(line: str) -> dict | None:
  """Parse a sim7600 ``+CGPSINFO: lat,N/S,lon,E/W,date,utc,alt,speed,course``."""
  body = _strip_prefix(line, "+CGPSINFO:")
  f = body.split(",")
  if len(f) < 9 or not f[0].strip():
    return None  # no fix -> all fields empty
  return _build(f[0], f[1], f[2], f[3], f[4], f[5], f[6], f[7], f[8])


def parse_cgnssinfo(line: str) -> dict | None:
  """Parse an A7670 ``+CGNSSINFO:`` reply.

  Field layout: mode, GPS-SVs, GLONASS-SVs, BEIDOU-SVs, lat, N/S, lon, E/W,
  date, UTC-time, alt, speed, course, PDOP, HDOP, VDOP.
  """
  body = _strip_prefix(line, "+CGNSSINFO:")
  f = body.split(",")
  if len(f) < 13 or not f[4].strip():
    return None  # no fix
  return _build(f[4], f[5], f[6], f[7], f[8], f[9], f[10], f[11], f[12])


def parse_gps_line(line: str) -> dict | None:
  """Dispatch by reply prefix to the matching parser."""
  upper = line.strip().upper()
  if upper.startswith("+CGPSINFO:"):
    return parse_cgpsinfo(line)
  if upper.startswith("+CGNSSINFO:"):
    return parse_cgnssinfo(line)
  return None
