# org_vrg_modem

Direct access to the USB modem over AT commands on its serial port (default
`/dev/ttyUSB2`), instead of going through ModemManager. Runs in the `vrg-modem`
service and owns the modem's AT port exclusively; its GPS and SMS features share
a single `AtTransport` (`sdk/at`) whose internal lock serialises access.

This plugin merges the former `org_vrg_gps` and `org_vrg_sms` plugins. All of its
videoreg-api methods are addressed under the `modem.` prefix (e.g.
`modem.get_location`, `modem.send_text`, `modem.modem_info`).

## GPS / location

GPS and LBS location are polled over AT (`AT+CGPS*` / `AT+CGNSS*` /
`AT+CLBS`, per modem family) and parsed in `sdk/at/gps.py` / `sdk/at/lbs.py`.
Tracks are written as GPX files to `~/.videoreg/gps/` (or `path.gps` from the
manifest). Implementation: `prod/modem.py` (interface in `modem.py`).

## SMS

Incoming SMS are read in PDU mode (`AT+CMGL`), multipart messages are merged,
and every part is deleted from the modem after reading. Sending encodes the text
into a PDU (`AT+CMGS`). Implementation: `prod/sms_manager.py` over `sdk/at`.

Received SMS are stored as JSON files in `~/.videoreg/sms/` (or `path.sms` from
the manifest).

**File name:** `YYYY-MM-DD_HH-MM-SS_<number>.json`
Example: `2026-03-24_14-30-45_79991234567.json` (the leading `+` is stripped).

**File structure:**
```json
{
  "number": "+79991234567",
  "text": "Message text",
  "timestamp": "2026-03-24T14:30:45.123456"
}
```

### SMS commands

If an incoming SMS starts with `/`, the plugin runs the matching api-command
(only from allowed numbers). The reply is sent back over SMS via the `sms`
gateway (`modem.send_text`).

Allowed numbers are read from `plugin_fields.org_vrg_sms.phone` in `users.json`.

## Modem info

`modem.modem_info` reads modem identity/operator/signal over AT
(`sdk/at/info.py`). `net.modem_info` falls back to it for modems ModemManager
does not manage (e.g. the A7670 over RNDIS).
