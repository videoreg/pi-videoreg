"""SMS PDU codec (3GPP TS 23.038 / 23.040).

Pure functions, no I/O. Decodes incoming SMS-DELIVER PDUs (as returned by
``AT+CMGL`` in PDU mode) and encodes outgoing SMS-SUBMIT PDUs (for
``AT+CMGS``). Handles the parts that make raw SMS non-trivial:

- GSM 7-bit default alphabet + single-shift extension table, with bit-level
  pack/unpack;
- UCS2 (UTF-16BE) for non-GSM text (e.g. Cyrillic);
- semi-octet (swapped-nibble BCD) phone numbers, incl. international and
  alphanumeric sender addresses;
- TP-SCTS service-centre timestamp with timezone;
- UDH (User Data Header) for concatenated / multipart messages.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# --- GSM 7-bit default alphabet (TS 23.038, positions 0x00..0x7F) ---------

GSM7_BASIC = (
  "@£$¥èéùìòÇ\nØø\rÅå"
  "Δ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ"
  " !\"#¤%&'()*+,-./"
  "0123456789:;<=>?"
  "¡ABCDEFGHIJKLMNO"
  "PQRSTUVWXYZÄÖÑÜ§"
  "¿abcdefghijklmno"
  "pqrstuvwxyzäöñüà"
)
assert len(GSM7_BASIC) == 128, len(GSM7_BASIC)

# Extension table: code after the ESC (0x1B) septet -> character.
GSM7_EXT = {
  0x0A: "\f",
  0x14: "^",
  0x28: "{",
  0x29: "}",
  0x2F: "\\",
  0x3C: "[",
  0x3D: "~",
  0x3E: "]",
  0x40: "|",
  0x65: "€",
}

# Reverse maps for encoding.
_GSM7_BASIC_REV = {ch: i for i, ch in enumerate(GSM7_BASIC)}
_GSM7_EXT_REV = {ch: code for code, ch in GSM7_EXT.items()}

ESC = 0x1B


# --- 7-bit bit packing ----------------------------------------------------


def unpack_7bit(data: bytes, count: int, skip_bits: int = 0) -> list[int]:
  """Unpack ``count`` 7-bit septets from packed octets (LSB-first).

  ``skip_bits`` discards leading fill bits (used when a UDH precedes 7-bit
  user data and the septet stream is realigned to a septet boundary).
  """
  septets: list[int] = []
  bitbuf = 0
  bitcount = 0
  for b in data:
    bitbuf |= b << bitcount
    bitcount += 8
    if skip_bits:
      drop = min(skip_bits, bitcount)
      bitbuf >>= drop
      bitcount -= drop
      skip_bits -= drop
    while bitcount >= 7:
      septets.append(bitbuf & 0x7F)
      bitbuf >>= 7
      bitcount -= 7
      if len(septets) == count:
        return septets
  return septets


def pack_7bit(septets: list[int]) -> bytes:
  """Pack 7-bit septets into octets (LSB-first)."""
  out = bytearray()
  bitbuf = 0
  bitcount = 0
  for s in septets:
    bitbuf |= (s & 0x7F) << bitcount
    bitcount += 7
    while bitcount >= 8:
      out.append(bitbuf & 0xFF)
      bitbuf >>= 8
      bitcount -= 8
  if bitcount > 0:
    out.append(bitbuf & 0xFF)
  return bytes(out)


def septets_to_text(septets: list[int]) -> str:
  """Map GSM 7-bit septets to a Unicode string, honouring the ESC table."""
  chars: list[str] = []
  i = 0
  n = len(septets)
  while i < n:
    s = septets[i]
    if s == ESC and i + 1 < n:
      i += 1
      chars.append(GSM7_EXT.get(septets[i], " "))
    else:
      chars.append(GSM7_BASIC[s])
    i += 1
  return "".join(chars)


def text_to_septets(text: str) -> list[int] | None:
  """Encode text to GSM 7-bit septets, or ``None`` if any char is unmapped."""
  septets: list[int] = []
  for ch in text:
    if ch in _GSM7_BASIC_REV:
      septets.append(_GSM7_BASIC_REV[ch])
    elif ch in _GSM7_EXT_REV:
      septets.append(ESC)
      septets.append(_GSM7_EXT_REV[ch])
    else:
      return None
  return septets


# --- semi-octet (BCD) numbers --------------------------------------------


def decode_semi_octets(data: bytes) -> str:
  """Decode swapped-nibble BCD digits; 0xF filler nibbles are dropped."""
  digits: list[str] = []
  for b in data:
    for nibble in (b & 0x0F, b >> 4):
      if nibble == 0x0F:
        continue
      digits.append("0123456789*#abc"[nibble] if nibble < 15 else "")
  return "".join(digits)


def encode_semi_octets(digits: str) -> bytes:
  """Encode decimal digits as swapped-nibble BCD, padding with 0xF."""
  if len(digits) % 2:
    digits += "F"
  out = bytearray()
  for i in range(0, len(digits), 2):
    lo = int(digits[i])
    hi = 0xF if digits[i + 1] == "F" else int(digits[i + 1])
    out.append((hi << 4) | lo)
  return bytes(out)


def _decode_address(addr_len: int, type_octet: int, value: bytes) -> str:
  """Decode an address field value given its length (in semi-octets) and type."""
  ton = (type_octet >> 4) & 0x07
  if ton == 0x05:  # alphanumeric — value is GSM 7-bit packed
    septet_count = (addr_len * 4) // 7
    return septets_to_text(unpack_7bit(value, septet_count))
  number = decode_semi_octets(value)
  if ton == 0x01:  # international
    number = "+" + number
  return number


# --- timestamp ------------------------------------------------------------


def decode_scts(data: bytes) -> datetime | None:
  """Decode a 7-octet TP-SCTS service-centre timestamp to an aware datetime."""
  if len(data) < 7:
    return None

  def swap(b: int) -> int:
    return (b & 0x0F) * 10 + (b >> 4)

  try:
    year = 2000 + swap(data[0])
    month = swap(data[1])
    day = swap(data[2])
    hour = swap(data[3])
    minute = swap(data[4])
    second = swap(data[5])
    tz_byte = data[6]
    tz_low = tz_byte & 0x0F
    tz_high = (tz_byte >> 4) & 0x0F
    sign = -1 if (tz_low & 0x08) else 1
    quarters = (tz_low & 0x07) * 10 + tz_high
    tz = timezone(sign * timedelta(minutes=quarters * 15))
    return datetime(year, month, day, hour, minute, second, tzinfo=tz)
  except (ValueError, IndexError):
    return None


# --- data coding scheme ---------------------------------------------------

ENC_7BIT = "7bit"
ENC_8BIT = "8bit"
ENC_UCS2 = "ucs2"


def dcs_encoding(dcs: int) -> str:
  """Map a TP-DCS byte to one of ENC_7BIT / ENC_8BIT / ENC_UCS2."""
  if dcs & 0x80 == 0:
    alphabet = dcs & 0x0C
    if alphabet == 0x00:
      return ENC_7BIT
    if alphabet == 0x04:
      return ENC_8BIT
    if alphabet == 0x08:
      return ENC_UCS2
    return ENC_7BIT
  if (dcs & 0xF0) == 0xF0:
    return ENC_8BIT if (dcs & 0x04) else ENC_7BIT
  return ENC_7BIT


# --- UDH (concatenation) --------------------------------------------------


@dataclass
class Concat:
  ref: int
  total: int
  seq: int


def parse_udh(udh: bytes) -> Concat | None:
  """Extract concatenation info from a UDH, if present (IEI 0x00 / 0x08)."""
  i = 0
  while i + 1 < len(udh):
    iei = udh[i]
    ielen = udh[i + 1]
    body = udh[i + 2 : i + 2 + ielen]
    if iei == 0x00 and len(body) == 3:
      return Concat(ref=body[0], total=body[1], seq=body[2])
    if iei == 0x08 and len(body) == 4:
      return Concat(ref=(body[0] << 8) | body[1], total=body[2], seq=body[3])
    i += 2 + ielen
  return None


# --- PDU decode -----------------------------------------------------------


@dataclass
class DecodedSms:
  sender: str
  text: str
  timestamp: datetime | None
  encoding: str
  concat: Concat | None = None
  smsc: str | None = None


def decode_deliver_pdu(pdu_hex: str) -> DecodedSms:
  """Decode an SMS-DELIVER PDU (hex string) into its fields."""
  data = bytes.fromhex(pdu_hex.strip())
  idx = 0

  smsc_len = data[idx]
  idx += 1
  smsc = None
  if smsc_len:
    smsc_type = data[idx]
    smsc = _decode_address(smsc_len * 2 - 2, smsc_type, data[idx + 1 : idx + smsc_len])
    idx += smsc_len

  first_octet = data[idx]
  idx += 1
  udhi = bool(first_octet & 0x40)

  addr_len = data[idx]  # in semi-octets (digits)
  idx += 1
  addr_type = data[idx]
  idx += 1
  addr_bytes = (addr_len + 1) // 2
  sender = _decode_address(addr_len, addr_type, data[idx : idx + addr_bytes])
  idx += addr_bytes

  idx += 1  # TP-PID
  dcs = data[idx]
  idx += 1
  encoding = dcs_encoding(dcs)

  timestamp = decode_scts(data[idx : idx + 7])
  idx += 7

  udl = data[idx]
  idx += 1
  ud = data[idx:]

  concat = None
  if udhi and ud:
    udhl = ud[0]
    concat = parse_udh(ud[1 : 1 + udhl])

  text = _decode_user_data(ud, udl, encoding, udhi)

  return DecodedSms(
    sender=sender,
    text=text,
    timestamp=timestamp,
    encoding=encoding,
    concat=concat,
    smsc=smsc,
  )


def _decode_user_data(ud: bytes, udl: int, encoding: str, udhi: bool) -> str:
  if encoding == ENC_7BIT:
    if udhi and ud:
      udhl = ud[0]
      header_octets = udhl + 1
      fill_bits = (7 - (header_octets * 8) % 7) % 7
      skipped = (header_octets * 8 + fill_bits) // 7
      septets = unpack_7bit(ud[header_octets:], udl - skipped, skip_bits=fill_bits)
    else:
      septets = unpack_7bit(ud, udl)
    return septets_to_text(septets)

  body = ud
  if udhi and ud:
    body = ud[1 + ud[0] :]
  if encoding == ENC_UCS2:
    return body.decode("utf-16-be", errors="replace")
  # 8-bit / binary
  return body.hex()


# --- PDU encode (SMS-SUBMIT) ----------------------------------------------


def encode_submit_pdu(number: str, text: str) -> tuple[int, str]:
  """Encode an SMS-SUBMIT PDU for AT+CMGS.

  Picks GSM 7-bit when the text fits the default alphabet, otherwise UCS2.
  Returns ``(tpdu_len, pdu_hex)`` where ``tpdu_len`` is the AT+CMGS length
  argument (octet count of everything after the SMSC field).
  """
  intl = number.startswith("+")
  digits = number.lstrip("+")
  addr_type = 0x91 if intl else 0x81

  septets = text_to_septets(text)
  if septets is not None:
    dcs = 0x00
    udl = len(septets)
    ud = pack_7bit(septets)
  else:
    dcs = 0x08
    ud = text.encode("utf-16-be")
    udl = len(ud)

  tpdu = bytearray()
  tpdu.append(0x01)  # SMS-SUBMIT, no validity period
  tpdu.append(0x00)  # TP-MR
  tpdu.append(len(digits))  # address length in semi-octets
  tpdu.append(addr_type)
  tpdu += encode_semi_octets(digits)
  tpdu.append(0x00)  # TP-PID
  tpdu.append(dcs)
  tpdu.append(udl)
  tpdu += ud

  pdu = bytes([0x00]) + bytes(tpdu)  # 0x00 = use modem's default SMSC
  return len(tpdu), pdu.hex().upper()
