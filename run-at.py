#!/usr/bin/env python3
"""vrg-at — direct AT-command tool for SMS & GPS over a modem's serial port.

Exercises the sdk/at toolkit against a real modem (default /dev/ttyUSB2) and
dumps raw responses alongside decoded results. Also runs an offline `selftest`
of the PDU and GPS parsers (no hardware needed).

NOTE: while ModemManager is still running it may hold /dev/ttyUSB2 open and
auto-read/delete incoming SMS, which can race with this tool. That is expected
for now (disabling ModemManager is a later step).
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sdk.at import gps as gpsmod  # noqa: E402
from sdk.at import sms as smsmod  # noqa: E402
from sdk.at.modem_info import ModemFamily, identify  # noqa: E402
from sdk.at.pdu import decode_deliver_pdu, encode_submit_pdu  # noqa: E402
from sdk.at.transport import AtTransport  # noqa: E402

DEFAULT_DEVICE = "/dev/ttyUSB2"


async def _open(args) -> AtTransport:
  t = AtTransport(device=args.dev)
  await t.open()
  return t


async def cmd_at(args) -> int:
  async with AtTransport(device=args.dev) as t:
    resp = await t.send(args.command, timeout=args.timeout)
    print(f"--- raw ({args.dev}) ---")
    print(resp.raw.strip() or "(no response)")
    print(f"--- final: {resp.final} ---")
  return 0 if resp.ok else 1


async def cmd_id(args) -> int:
  async with AtTransport(device=args.dev) as t:
    family, model = await identify(t)
    print(f"model:  {model or '(unknown)'}")
    print(f"family: {family.value}")
  return 0


async def cmd_sms_list(args) -> int:
  async with AtTransport(device=args.dev) as t:
    messages = await smsmod.list_incoming(t)
  if not messages:
    print("(no messages)")
    return 0
  for m in messages:
    d = m.decoded
    print(f"=== index {m.index} ===")
    print(f"  raw pdu : {m.pdu}")
    print(f"  sender  : {d.sender}")
    print(f"  text    : {d.text!r}")
    print(f"  time    : {d.timestamp}")
    print(f"  encoding: {d.encoding}")
    if d.concat:
      print(f"  part    : {d.concat.seq}/{d.concat.total} (ref {d.concat.ref})")
  return 0


async def cmd_sms_send(args) -> int:
  tpdu_len, pdu_hex = encode_submit_pdu(args.number, args.text)
  print(f"pdu ({tpdu_len} octets): {pdu_hex}")
  async with AtTransport(device=args.dev) as t:
    _, resp = await smsmod.send(t, args.number, args.text)
  print(f"--- raw ---\n{resp.raw.strip()}")
  print(f"--- final: {resp.final} ---")
  return 0 if resp.ok else 1


async def cmd_gps(args) -> int:
  async with AtTransport(device=args.dev) as t:
    family, model = await identify(t)
    print(f"family: {family.value} ({model})")

    if family == ModemFamily.A7670:
      enable, query, prefix = "AT+CGNSSPWR=1", "AT+CGNSSINFO", "+CGNSSINFO:"
    else:  # SIM7600 and default
      enable, query, prefix = "AT+CGPS=1", "AT+CGPSINFO", "+CGPSINFO:"

    await t.send(enable)
    for attempt in range(args.attempts):
      resp = await t.send(query)
      line = resp.line_after(prefix)
      print(f"[{attempt + 1}] raw: {line}")
      if line:
        parsed = gpsmod.parse_gps_line(line)
        if parsed:
          print(f"    parsed: {parsed}")
          return 0
      if attempt < args.attempts - 1:
        await asyncio.sleep(args.interval)
  print("no fix")
  return 1


# --- offline selftest -----------------------------------------------------

# Authoritative GSM 7-bit SMS-DELIVER (Wikipedia): sender +31641600986.
_PDU_GSM7 = "07911326040000F0040B911346610089F60000208062917314080CC8F71D14969741F977FD07"
# UCS2 "Привет".
_PDU_UCS2 = "00040B911346610089F6000820806291731400" + "0C" + "041F0440043804320435 0442".replace(" ", "")
# 7-bit concatenated part (UDH ref 0xAB, 1/2), text "Hi".
_PDU_UDH = "00440B911346610089F6000020806291731400" + "09" + "050003AB02019069"


def _selftest() -> int:
  failures = []

  def check(name, got, expected):
    status = "ok " if got == expected else "FAIL"
    if got != expected:
      failures.append(name)
    print(f"  [{status}] {name}: {got!r}" + ("" if got == expected else f" != {expected!r}"))

  print("SMS PDU decode:")
  d = decode_deliver_pdu(_PDU_GSM7)
  check("gsm7.sender", d.sender, "+31641600986")
  check("gsm7.text", d.text, "How are you?")
  check("gsm7.smsc", d.smsc, "+31624000000")

  d = decode_deliver_pdu(_PDU_UCS2)
  check("ucs2.text", d.text, "Привет")
  check("ucs2.encoding", d.encoding, "ucs2")

  d = decode_deliver_pdu(_PDU_UDH)
  check("udh.text", d.text, "Hi")
  check("udh.concat", (d.concat.ref, d.concat.total, d.concat.seq), (0xAB, 2, 1))

  print("SMS PDU encode:")
  _, h = encode_submit_pdu("+79991234567", "Hello")
  check("encode.gsm7.tail", h.endswith("C8329BFD06"), True)
  _, h = encode_submit_pdu("+79991234567", "Привет")
  # layout: SMSC(1) FO(1) MR(1) ALEN(1) TYPE(1) ADDR(6) PID(1) DCS(1) ...
  check("encode.ucs2.dcs", h[24:26], "08")

  print("GPS parse:")
  g = gpsmod.parse_cgpsinfo("+CGPSINFO: 5956.165420,N,03019.551200,E,270626,103045.0,12.3,0.5,84.2")
  check("cgpsinfo.lat", g["latitude"], 59.93609)
  check("cgpsinfo.lon", g["longitude"], 30.325853)
  g = gpsmod.parse_cgnssinfo(
    "+CGNSSINFO: 3,09,05,00,5930.000000,S,03000.000000,W,270626,103045.0,1,2,3,1,1,1"
  )
  check("cgnssinfo.lat_neg", g["latitude"], -59.5)
  check("cgnssinfo.lon_neg", g["longitude"], -30.0)
  check("nofix", gpsmod.parse_cgpsinfo("+CGPSINFO: ,,,,,,,,"), None)

  print()
  if failures:
    print(f"SELFTEST FAILED: {len(failures)} -> {failures}")
    return 1
  print("SELFTEST OK")
  return 0


async def cmd_selftest(args) -> int:
  return _selftest()


def main() -> int:
  parser = argparse.ArgumentParser(prog="vrg-at", description=__doc__)
  parser.add_argument("--dev", default=DEFAULT_DEVICE, help=f"serial device (default {DEFAULT_DEVICE})")
  sub = parser.add_subparsers(dest="cmd", required=True)

  p = sub.add_parser("at", help="send a raw AT command")
  p.add_argument("command")
  p.add_argument("--timeout", type=float, default=5.0)
  p.set_defaults(func=cmd_at)

  p = sub.add_parser("id", help="detect modem family")
  p.set_defaults(func=cmd_id)

  p = sub.add_parser("sms-list", help="list & decode stored SMS")
  p.set_defaults(func=cmd_sms_list)

  p = sub.add_parser("sms-send", help="encode & send an SMS")
  p.add_argument("number")
  p.add_argument("text")
  p.set_defaults(func=cmd_sms_send)

  p = sub.add_parser("gps", help="enable GNSS and poll a location fix")
  p.add_argument("--attempts", type=int, default=10)
  p.add_argument("--interval", type=float, default=2.0)
  p.set_defaults(func=cmd_gps)

  p = sub.add_parser("selftest", help="offline parser self-test (no hardware)")
  p.set_defaults(func=cmd_selftest)

  args = parser.parse_args()
  return asyncio.run(args.func(args))


if __name__ == "__main__":
  sys.exit(main())
