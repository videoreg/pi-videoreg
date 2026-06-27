"""LBS (cell-based) location over AT — SIMCom ``AT+CLBS``.

Unlike GPS, LBS asks the SIMCom LBS server to estimate the position from the
serving cell. That means it needs the modem to be network-attached with a data
(PDP) context, but it returns coordinates already in **decimal degrees** (no
NMEA conversion). Supported on both SIM7600 and A7670 (both SIMCom).

Reply: ``+CLBS: <location_code>[,<lat>,<lon>,<accuracy>]`` where
``location_code == 0`` means success; any other value is an error.
"""

import re

from sdk.at.transport import AtTransport

_CLBS_RE = re.compile(r"\+CLBS:\s*(-?\d+)(?:,([-\d.]+),([-\d.]+),(\d+))?")


def parse_clbs(line: str) -> dict | None:
  """Parse a ``+CLBS:`` reply. Returns at least ``{location_code}``; on success
  also ``latitude`` / ``longitude`` / ``accuracy`` (metres)."""
  m = _CLBS_RE.search(line)
  if not m:
    return None
  result: dict = {"location_code": int(m.group(1))}
  if result["location_code"] == 0 and m.group(2) is not None:
    try:
      result["latitude"] = float(m.group(2))
      result["longitude"] = float(m.group(3))
      result["accuracy"] = int(m.group(4))
    except (ValueError, TypeError):
      pass
  return result


async def get_lbs(transport: AtTransport, cid: int = 1, timeout: float = 20.0):
  """Query LBS location. Returns ``(raw_line, parsed_dict_or_None)``.

  The query talks to the SIMCom LBS server over the data context, so it can
  take several seconds and fails if the modem is not attached / has no data.
  """
  resp = await transport.send(f"AT+CLBS=4,{cid}", timeout=timeout)
  line = resp.line_after("+CLBS:")
  return line, (parse_clbs(line) if line else None)
