"""High-level SMS helpers over the AT transport (PDU mode).

Combines ``transport`` with the ``pdu`` codec. Still plugin-agnostic — these
are the building blocks a future SmsManager backend (and the vrg-at CLI) use.
"""

from dataclasses import dataclass, field
from datetime import datetime

from sdk.at.pdu import DecodedSms, decode_deliver_pdu, encode_submit_pdu
from sdk.at.transport import AtResponse, AtTransport


@dataclass
class IncomingSms:
  """A single raw storage slot as returned by AT+CMGL (may be one part of many)."""

  index: int
  pdu: str
  decoded: DecodedSms


@dataclass
class Sms:
  """A complete message — multipart parts already merged into one."""

  number: str  # sender phone number
  text: str
  timestamp: datetime | None
  indices: list[int] = field(default_factory=list)  # storage slots of all parts (for deletion)


async def set_pdu_mode(transport: AtTransport) -> None:
  await transport.send("AT+CMGF=0")


async def list_incoming(transport: AtTransport) -> list[IncomingSms]:
  """List all stored messages via ``AT+CMGL=4`` and decode each PDU.

  In PDU mode ``+CMGL`` emits a header line (``+CMGL: idx,stat,alpha,len``)
  followed by the raw PDU hex on the next line.
  """
  await set_pdu_mode(transport)
  resp = await transport.send("AT+CMGL=4", timeout=10.0)

  result: list[IncomingSms] = []
  lines = resp.lines
  i = 0
  while i < len(lines):
    line = lines[i]
    if line.startswith("+CMGL:"):
      try:
        index = int(line.split(":", 1)[1].split(",")[0].strip())
      except (ValueError, IndexError):
        i += 1
        continue
      pdu = lines[i + 1] if i + 1 < len(lines) else ""
      if pdu:
        try:
          result.append(IncomingSms(index=index, pdu=pdu, decoded=decode_deliver_pdu(pdu)))
        except Exception:  # noqa: BLE001 — surface raw PDU even if decode fails
          pass
      i += 2
    else:
      i += 1
  return result


def merge_parts(parts: list[IncomingSms]) -> list[Sms]:
  """Merge multipart SMS into whole messages.

  Concatenated parts (same sender + UDH reference + total count) are joined in
  sequence order; the text is concatenated, the timestamp is taken from the
  first part, and all part storage indices are kept for later deletion.
  Non-concatenated messages pass through unchanged.
  """
  groups: dict[tuple, list[IncomingSms]] = {}
  order: list[tuple] = []
  for p in parts:
    c = p.decoded.concat
    key = (p.decoded.sender, c.ref, c.total) if c else ("single", p.index)
    if key not in groups:
      groups[key] = []
      order.append(key)
    groups[key].append(p)

  messages: list[Sms] = []
  for key in order:
    items = sorted(groups[key], key=lambda x: x.decoded.concat.seq if x.decoded.concat else 0)
    messages.append(
      Sms(
        number=items[0].decoded.sender,
        text="".join(it.decoded.text for it in items),
        timestamp=items[0].decoded.timestamp,
        indices=[it.index for it in items],
      )
    )
  return messages


async def list_messages(transport: AtTransport) -> list[Sms]:
  """List incoming SMS as whole messages, with multipart parts already merged."""
  return merge_parts(await list_incoming(transport))


async def delete(transport: AtTransport, index: int) -> AtResponse:
  return await transport.send(f"AT+CMGD={index}")


async def send(transport: AtTransport, number: str, text: str) -> tuple[str, AtResponse]:
  """Encode ``text`` to a SUBMIT PDU and send it. Returns ``(pdu_hex, response)``."""
  await set_pdu_mode(transport)
  tpdu_len, pdu_hex = encode_submit_pdu(number, text)
  resp = await transport.send_pdu(f"AT+CMGS={tpdu_len}", pdu_hex)
  return pdu_hex, resp
