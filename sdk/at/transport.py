"""Async AT-over-serial transport (pyserial + asyncio).

Talks to a modem's raw AT port (e.g. /dev/ttyUSB2). pyserial is blocking, so
reads/writes run in the default executor (same approach as
``sdk/folder_watcher.py``). A per-transport ``asyncio.Lock`` serialises access
because a single port (ttyUSB2) is shared between SMS and GPS polling.

``serial`` is imported lazily inside ``open()`` so that the pure ``pdu`` / ``gps``
modules — and the offline ``selftest`` — work without pyserial installed.
"""

import asyncio
import re
from dataclasses import dataclass, field
from logging import Logger

_FINAL_RE = re.compile(r"\r\n(OK|ERROR|\+CME ERROR:[^\r]*|\+CMS ERROR:[^\r]*)\r\n")
_ERROR_PREFIXES = ("+CME ERROR", "+CMS ERROR")


@dataclass
class AtResponse:
  command: str
  lines: list[str] = field(default_factory=list)  # informational lines (no echo, no final code)
  final: str | None = None  # "OK" / "ERROR" / "+CME ERROR: ..." / None on timeout
  raw: str = ""

  @property
  def ok(self) -> bool:
    return self.final == "OK"

  def line_after(self, prefix: str) -> str | None:
    """First informational line starting with ``prefix`` (e.g. ``+CGPSINFO:``)."""
    for line in self.lines:
      if line.startswith(prefix):
        return line
    return None


class AtTransport:
  def __init__(
    self,
    device: str = "/dev/ttyUSB2",
    baudrate: int = 115200,
    logger: Logger | None = None,
  ):
    self._device = device
    self._baudrate = baudrate
    self._logger = logger
    self._ser = None
    self._lock = asyncio.Lock()
    # Cached modem identity (filled once by modem_info.identify); lives as long
    # as this open port, so detection is not repeated on every read/send.
    self.family = None  # ModemFamily | None
    self.model: str | None = None

  # --- lifecycle ----------------------------------------------------------

  async def open(self) -> None:
    import serial  # lazy: keep pdu/gps importable without pyserial

    loop = asyncio.get_event_loop()
    self._ser = await loop.run_in_executor(
      None,
      lambda: serial.Serial(
        self._device,
        self._baudrate,
        timeout=0.1,
        write_timeout=2.0,
      ),
    )
    # Drain any stale bytes left in the buffer.
    await loop.run_in_executor(None, self._ser.reset_input_buffer)

  async def close(self) -> None:
    if self._ser is not None:
      loop = asyncio.get_event_loop()
      await loop.run_in_executor(None, self._ser.close)
      self._ser = None

  async def __aenter__(self) -> "AtTransport":
    await self.open()
    return self

  async def __aexit__(self, *exc) -> None:
    await self.close()

  # --- low-level I/O ------------------------------------------------------

  async def _write(self, data: bytes) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, self._ser.write, data)

  async def _read_until(self, predicate, timeout: float) -> bytes:
    """Accumulate bytes until ``predicate(buffer)`` is true or ``timeout``."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    buf = bytearray()
    while loop.time() < deadline:
      chunk = await loop.run_in_executor(None, self._ser.read, 256)
      if chunk:
        buf += chunk
        if predicate(buf):
          break
      else:
        await asyncio.sleep(0.02)
    return bytes(buf)

  # --- AT commands --------------------------------------------------------

  async def send(self, command: str, timeout: float = 5.0) -> AtResponse:
    """Send a single AT command and return the parsed response."""
    async with self._lock:
      if self._logger:
        self._logger.debug(f"AT >> {command}")
      await self._write((command + "\r").encode())
      raw = await self._read_until(lambda b: _FINAL_RE.search(b.decode(errors="replace")), timeout)
      resp = self._parse(command, raw)
      if self._logger:
        self._logger.debug(f"AT << {resp.final} {resp.lines}")
      return resp

  async def send_pdu(self, command: str, pdu_hex: str, timeout: float = 10.0) -> AtResponse:
    """Send a PDU-mode command (AT+CMGS=<len>): await '>' then write PDU + Ctrl-Z."""
    async with self._lock:
      if self._logger:
        self._logger.debug(f"AT >> {command} (pdu {pdu_hex})")
      await self._write((command + "\r").encode())
      await self._read_until(lambda b: b">" in b, timeout=5.0)
      await self._write(pdu_hex.encode() + b"\x1a")  # Ctrl-Z submits
      raw = await self._read_until(
        lambda b: _FINAL_RE.search(b.decode(errors="replace")), timeout
      )
      return self._parse(command, raw)

  # --- parsing ------------------------------------------------------------

  @staticmethod
  def _parse(command: str, raw: bytes) -> AtResponse:
    text = raw.decode(errors="replace")
    lines = [ln.strip() for ln in text.replace("\r", "\n").split("\n")]
    lines = [ln for ln in lines if ln]
    if lines and lines[0] == command:  # drop command echo
      lines = lines[1:]

    final = None
    body = []
    for ln in lines:
      if ln in ("OK", "ERROR") or ln.startswith(_ERROR_PREFIXES):
        final = ln
      else:
        body.append(ln)
    return AtResponse(command=command, lines=body, final=final, raw=text)
