"""Modem family detection over AT.

GPS enable commands and location-reply formats differ between modem families,
so callers identify the modem first and branch accordingly:

- SIM7600 / SIM7xxx: ``AT+CGPS=1``  -> ``AT+CGPSINFO``
- A7670   / A76xx:   ``AT+CGNSSPWR=1`` -> ``AT+CGNSSINFO``
"""

from enum import Enum

from sdk.at.transport import AtTransport


class ModemFamily(str, Enum):
  SIM7600 = "SIM7600"
  A7670 = "A7670"
  UNKNOWN = "UNKNOWN"


def family_from_model(model: str) -> ModemFamily:
  """Classify a model string (from AT+CGMM / ATI) into a family."""
  m = model.upper()
  if "A7670" in m or "A76" in m:
    return ModemFamily.A7670
  if "SIM7600" in m or "SIM76" in m:
    return ModemFamily.SIM7600
  return ModemFamily.UNKNOWN


async def identify(transport: AtTransport) -> tuple[ModemFamily, str]:
  """Query the modem model and return ``(family, raw_model_string)``."""
  resp = await transport.send("AT+CGMM")
  model = " ".join(resp.lines) if resp.lines else ""
  if not model:
    resp = await transport.send("ATI")
    model = " ".join(resp.lines)
  return family_from_model(model), model
