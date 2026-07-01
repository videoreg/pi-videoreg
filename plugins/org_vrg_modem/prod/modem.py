import asyncio
from logging import Logger

from plugins.org_vrg_modem.modem import Modem
from sdk.at import gps as at_gps
from sdk.at import lbs as at_lbs
from sdk.at.modem_info import ModemFamily, identify
from sdk.at.transport import AtTransport


class ModemImpl(Modem):
  """GPS / LBS location over the modem's raw AT port (no ModemManager / mmcli).

  Location is obtained by polling a single AT command and parsing its reply:
  ``AT+CGPSINFO`` on SIM7600, ``AT+CGNSSINFO`` on A7670 (coordinates converted
  from NMEA ddmm.mmmm to decimal degrees in ``sdk/at/gps.py``). The modem family
  is detected once and cached on the transport.

  The AtTransport is shared with the SMS plugin (same vrg-modem process): it
  opens the serial port once, serialises access via its internal lock, and
  self-heals on port errors — so this modem never opens or closes it directly.
  """

  def __init__(self, logger: Logger, transport: AtTransport):
    self._logger = logger
    self._transport = transport
    self._enabled = False
    self._family = ModemFamily.UNKNOWN
    self._model: str | None = None

  @property
  def modem_id(self) -> str | None:
    # Identity used by the plugin to detect modem re-enumeration; the model
    # string is stable for a given modem on a given port.
    return self._model if self._enabled else None

  def is_enabled(self) -> bool:
    return self._enabled

  # --- per-family command set ---------------------------------------------

  def _gps_commands(self) -> tuple[str, str, str, str, str]:
    """Return (power_on, power_off, query_state, info, info_prefix) for the family."""
    if self._family == ModemFamily.A7670:
      return "AT+CGNSSPWR=1", "AT+CGNSSPWR=0", "AT+CGNSSPWR?", "AT+CGNSSINFO", "+CGNSSINFO:"
    return "AT+CGPS=1", "AT+CGPS=0", "AT+CGPS?", "AT+CGPSINFO", "+CGPSINFO:"

  @staticmethod
  def _state_is_on(line: str) -> bool:
    # "+CGPS: 1,1" / "+CGNSSPWR: 1" -> first value after ':' is 1.
    if ":" not in line:
      return False
    first = line.split(":", 1)[1].split(",")[0].strip()
    return first == "1"

  # --- Modem interface ----------------------------------------------------

  async def _ping(self, attempts: int = 3) -> bool:
    """Probe with AT a few times — the first command after opening a port is
    often dropped, and modems can be briefly busy."""
    for _ in range(attempts):
      resp = await self._transport.send("AT", timeout=3.0)
      if resp.ok:
        return True
      await asyncio.sleep(0.5)
    return False

  async def enable(self) -> bool:
    try:
      if not await self._ping():
        self._logger.warning(f"modem not responding to AT on {self._transport.device}")
        self._enabled = False
        return False
      family, model = await identify(self._transport)  # cached on the transport
      self._family = family
      self._model = model or self._transport.device
      self._enabled = True
      return True
    except Exception as e:
      self._logger.warning(f"modem enable error: {e}")
      self._enabled = False
      return False

  async def _ensure_enabled(self) -> bool:
    """Enable the modem on demand (e.g. when a command queries location while the
    background monitor is not running). Returns False instead of raising."""
    if self._enabled:
      return True
    return await self.enable()

  async def enable_gps(self) -> bool:
    if not await self._ensure_enabled():
      return False
    try:
      power_on, _, query, _, _ = self._gps_commands()

      state = await self._transport.send(query, timeout=3.0)
      if state.ok and state.lines and self._state_is_on(state.lines[0]):
        return True

      resp = await self._transport.send(power_on, timeout=5.0)
      if resp.ok:
        return True

      # Some firmwares reply ERROR when GPS is already powered — re-check state.
      state = await self._transport.send(query, timeout=3.0)
      return state.ok and bool(state.lines) and self._state_is_on(state.lines[0])
    except Exception as e:
      self._logger.warning(f"enable gps error: {e}")
      return False

  async def disable_gps(self) -> bool:
    if not self._enabled:
      return False
    try:
      _, power_off, _, _, _ = self._gps_commands()
      resp = await self._transport.send(power_off, timeout=5.0)
      return resp.ok
    except Exception as e:
      self._logger.warning(f"disable gps error: {e}")
      return False

  async def get_location_gps(self) -> dict | None:
    if not await self._ensure_enabled():
      return None
    try:
      _, _, _, info, prefix = self._gps_commands()
      resp = await self._transport.send(info, timeout=3.0)
      line = resp.line_after(prefix)
      if not line:
        return None
      return at_gps.parse_gps_line(line)  # decimal degrees, speed km/h, or None
    except Exception as e:
      self._logger.warning(f"get gps location error: {e}")
      return None

  async def enable_lbs(self) -> bool:
    # LBS is queried on demand via AT+CLBS; there is nothing to keep enabled.
    return True

  async def get_location_lbs(self) -> dict | None:
    if not await self._ensure_enabled():
      return None
    try:
      _, parsed = await at_lbs.get_lbs(self._transport, cid=1, timeout=15.0)
      if parsed and "latitude" in parsed:
        return {
          "latitude": parsed["latitude"],
          "longitude": parsed["longitude"],
          "accuracy": parsed.get("accuracy"),
        }
      return None
    except Exception as e:
      self._logger.warning(f"get lbs location error: {e}")
      return None
