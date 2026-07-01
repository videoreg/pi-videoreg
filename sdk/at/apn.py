"""APN (PDP context) config over AT — SIMCom ``AT+CGDCONT``.

The APN lives on the modem itself: it is written to the primary PDP context
(CID 1) and applied by re-attaching the radio. This works the same on SIM7600
and A7670 (both SIMCom). For an RNDIS modem it is the only way to set the APN —
there is no ModemManager / NetworkManager ``gsm`` profile involved; the module
dials the context internally using this APN.

Reply to ``AT+CGDCONT?`` is one line per context::

    +CGDCONT: 1,"IP","internet",...

Note: on a modem managed by ModemManager (SIM7600/QMI) MM may re-apply its own
APN from the connection profile when it reconnects, so the AT value can be
overridden there. On RNDIS (A7670) this AT value is authoritative.
"""

import asyncio
import re

from sdk.at.transport import AtTransport

# Primary context (CID 1): +CGDCONT: 1,"<pdp_type>","<apn>",...
_CGDCONT_RE = re.compile(r'\+CGDCONT:\s*1,"[^"]*","([^"]*)"')


def parse_cgdcont(lines: list[str]) -> str | None:
  """Return the APN of PDP context 1 from ``AT+CGDCONT?`` output, or None."""
  for line in lines:
    m = _CGDCONT_RE.search(line)
    if m:
      return m.group(1)
  return None


async def get_apn(transport: AtTransport) -> str | None:
  """Read the APN of the primary PDP context. ``None`` if the query fails.

  An empty string means the context is set to auto/blank APN.
  """
  resp = await transport.send("AT+CGDCONT?", timeout=5.0)
  if not resp.ok:
    return None
  return parse_cgdcont(resp.lines) or ""


async def set_apn(transport: AtTransport, apn: str) -> bool:
  """Write the APN to the primary PDP context and re-attach the radio.

  An empty ``apn`` clears the context (operator/auto APN). Returns True on
  success. The radio is cycled with ``AT+CFUN=0/1`` so the new APN is used for
  the next data call; this briefly drops the cellular connection (and any GNSS
  session) but does not re-enumerate the USB ports.
  """
  resp = await transport.send(f'AT+CGDCONT=1,"IP","{apn}"', timeout=5.0)
  if not resp.ok:
    return False

  # Re-attach so the modem re-dials the context with the new APN.
  await transport.send("AT+CFUN=0", timeout=10.0)
  await asyncio.sleep(2)
  await transport.send("AT+CFUN=1", timeout=10.0)
  return True
