"""Direct AT-command access to USB modems (sim7600, A7670).

This package provides a small, dependency-light toolkit for talking to a
cellular modem over its raw serial AT interface (e.g. /dev/ttyUSB2), instead
of going through ModemManager:

- ``transport`` — async AT-over-serial transport (pyserial + asyncio).
- ``pdu``       — SMS PDU decode/encode (GSM 7-bit, UCS2, multipart UDH).
- ``gps``       — +CGPSINFO / +CGNSSINFO coordinate parsing.
- ``modem_info``— modem family detection.
- ``sms``       — high-level list/delete/send helpers built on the above.

The ``pdu`` and ``gps`` modules are pure (no I/O) and unit-testable; importing
them does not require pyserial.
"""
