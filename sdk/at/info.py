"""Modem info over AT — manufacturer, model, operator, signal, access tech.

Returns the same dict shape as the ModemManager/mmcli path in
``plugins/org_vrg_net/prod/modem_controls.py`` so both paths feed the UI
identically::

    {connected, device, manufacturer, model, operator, access_tech, signal_quality}

This is the fallback used for modems that ModemManager does not manage (e.g. the
A7670 exposed only over RNDIS): the cellular identity is read directly from the
modem's AT port instead of from mmcli.
"""

import re

from sdk.at.transport import AtTransport

# AT+COPS? access-technology (<AcT>) codes -> UI label (matches the labels
# produced by the mmcli path's _extract_access_tech).
_ACT_LABELS = {
  0: "2G",  # GSM
  1: "2G",  # GSM Compact
  2: "3G",  # UTRAN
  3: "2G",  # GSM w/EGPRS
  4: "3G",  # UTRAN w/HSDPA
  5: "3G",  # UTRAN w/HSUPA
  6: "3G",  # UTRAN w/HSDPA+HSUPA
  7: "4G LTE",  # E-UTRAN
  8: "2G",  # EC-GSM-IoT
  9: "4G",  # E-UTRAN NB-S1
  10: "5G",  # E-UTRA connected to a 5GCN
  11: "5G",  # NR connected to a 5GCN
  12: "5G",  # NG-RAN
  13: "5G",  # E-UTRA-NR dual connectivity
}

_COPS_RE = re.compile(r'\+COPS:\s*\d+(?:,\s*(\d+)\s*,\s*"([^"]*)"(?:\s*,\s*(\d+))?)?')
_CSQ_RE = re.compile(r"\+CSQ:\s*(\d+),")


def parse_cops(line: str) -> tuple[str | None, str | None]:
  """Parse ``+COPS: <mode>,<format>,"<oper>",<AcT>``.

  Returns ``(operator_name, access_tech_label)``. Either may be ``None`` when
  the modem is not registered (``+COPS: 0`` with no operator) or the fields are
  absent.
  """
  m = _COPS_RE.search(line)
  if not m:
    return None, None
  operator = m.group(2) or None
  act = _ACT_LABELS.get(int(m.group(3))) if m.group(3) is not None else None
  return operator, act


def parse_csq(line: str) -> int | None:
  """Parse ``+CSQ: <rssi>,<ber>`` and return signal quality as a 0-100 percent.

  ``rssi`` is 0-31 (99 means unknown -> ``None``).
  """
  m = _CSQ_RE.search(line)
  if not m:
    return None
  rssi = int(m.group(1))
  if rssi >= 99:
    return None
  return round(rssi * 100 / 31)


async def get_modem_info(transport: AtTransport) -> dict:
  """Read modem info over AT. Mirrors the mmcli path's return shape.

  ``{"connected": False}`` if the modem does not answer AT (no model), otherwise
  a full info dict. Individual fields are ``None`` when their command fails, so a
  registered-but-quiet modem still reports as connected.
  """
  cgmm = await transport.send("AT+CGMM", timeout=3.0)
  model = cgmm.lines[0] if cgmm.ok and cgmm.lines else None
  if not model:
    return {"connected": False}

  cgmi = await transport.send("AT+CGMI", timeout=3.0)
  manufacturer = cgmi.lines[0] if cgmi.ok and cgmi.lines else None

  cops = await transport.send("AT+COPS?", timeout=5.0)
  operator, access_tech = (None, None)
  cops_line = cops.line_after("+COPS:")
  if cops_line:
    operator, access_tech = parse_cops(cops_line)

  csq = await transport.send("AT+CSQ", timeout=3.0)
  signal_quality = None
  csq_line = csq.line_after("+CSQ:")
  if csq_line:
    signal_quality = parse_csq(csq_line)

  return {
    "connected": True,
    "device": transport.device,
    "manufacturer": manufacturer,
    "model": model,
    "operator": operator,
    "access_tech": access_tech,
    "signal_quality": signal_quality,
  }
