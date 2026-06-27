import asyncio
from logging import Logger

from plugins.org_vrg_gps.modem import Modem
from sdk.at import gps as at_gps
from sdk.at import lbs as at_lbs
from sdk.at.modem_info import ModemFamily, identify
from sdk.at.transport import AtTransport

# GPS uses its own AT port (ttyUSB3) so it doesn't contend with the SMS plugin
# on ttyUSB2 — the two run in separate service processes.
DEFAULT_DEVICE = "/dev/ttyUSB3"


class ModemImpl(Modem):
  """GPS / LBS location over the modem's raw AT port (no ModemManager / mmcli).

  Location is obtained by polling a single AT command and parsing its reply:
  ``AT+CGPSINFO`` on SIM7600, ``AT+CGNSSINFO`` on A7670 (coordinates converted
  from NMEA ddmm.mmmm to decimal degrees in ``sdk/at/gps.py``). The modem family
  is detected once and cached on the transport. A single AtTransport is kept open
  and reused; its internal lock serialises GPS and LBS queries.
  """

  def __init__(self, logger: Logger, device: str = DEFAULT_DEVICE, baudrate: int = 115200):
    self._logger = logger
    self._device = device
    self._baudrate = baudrate
    self._transport: AtTransport | None = None
    self._open_lock = asyncio.Lock()
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

  # --- transport lifecycle ------------------------------------------------

  async def _get_transport(self) -> AtTransport:
    if self._transport is None:
      async with self._open_lock:
        if self._transport is None:
          transport = AtTransport(self._device, self._baudrate, self._logger)
          await transport.open()
          self._transport = transport
    return self._transport

  async def _reset(self) -> None:
    self._enabled = False
    if self._transport is not None:
      try:
        await self._transport.close()
      except Exception as e:
        self._logger.debug(f"transport close error: {e}")
      self._transport = None

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

  async def enable(self) -> bool:
    try:
      transport = await self._get_transport()
      resp = await transport.send("AT", timeout=2.0)
      if not resp.ok:
        self._logger.warning("modem not responding to AT")
        await self._reset()
        return False
      family, model = await identify(transport)  # cached on the transport
      self._family = family
      self._model = model or self._device
      self._enabled = True
      return True
    except Exception as e:
      self._logger.warning(f"modem enable error: {e}")
      await self._reset()
      return False

  async def enable_gps(self) -> bool:
    if not self._enabled:
      raise Exception("Modem not enabled!")
    try:
      transport = await self._get_transport()
      power_on, _, query, _, _ = self._gps_commands()

      state = await transport.send(query, timeout=3.0)
      if state.ok and state.lines and self._state_is_on(state.lines[0]):
        return True

      resp = await transport.send(power_on, timeout=5.0)
      if resp.ok:
        return True

      # Some firmwares reply ERROR when GPS is already powered — re-check state.
      state = await transport.send(query, timeout=3.0)
      return state.ok and bool(state.lines) and self._state_is_on(state.lines[0])
    except Exception as e:
      self._logger.warning(f"enable gps error: {e}")
      return False

  async def disable_gps(self) -> bool:
    if not self._enabled:
      raise Exception("Modem not enabled!")
    try:
      transport = await self._get_transport()
      _, power_off, _, _, _ = self._gps_commands()
      resp = await transport.send(power_off, timeout=5.0)
      return resp.ok
    except Exception as e:
      self._logger.warning(f"disable gps error: {e}")
      return False

  async def get_location_gps(self) -> dict | None:
    if not self._enabled:
      raise Exception("Modem not enabled!")
    try:
      transport = await self._get_transport()
      _, _, _, info, prefix = self._gps_commands()
      resp = await transport.send(info, timeout=3.0)
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
    if not self._enabled:
      raise Exception("Modem not enabled!")
    try:
      transport = await self._get_transport()
      _, parsed = await at_lbs.get_lbs(transport, cid=1, timeout=15.0)
      if parsed and "latitude" in parsed:
        return {
          "latitude": parsed["latitude"],
          "longitude": parsed["longitude"],
          "accuracy": parsed["accuracy"],
        }
      return None
    except Exception as e:
      self._logger.warning(f"get lbs location error: {e}")
      return None
