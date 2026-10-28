"""WireGuard config: form settings <-> `/etc/wireguard/wg0.conf`.

The config is never edited as text. The web UI edits a fixed set of fields (one interface,
one peer — the VPN server) and the file is generated from them, so that the parts videoreg
relies on are always there: `Table = off` (wg-quick installs no routes, the tunnel never
becomes the default route) and the PostUp / PreDown hooks of task/net/wg-routes.sh, which
set up source-based policy routing instead. DNS is not supported: the system resolver must
not depend on the tunnel being up.

The generated file is also the only place the settings are stored: the form is filled by
parsing it back. A config made elsewhere (e.g. by a VPN server panel) is imported the same
way; whatever the form does not support is reported as ignored.
"""

import base64
import ipaddress
import re

ROUTING_SCRIPT_MARK = "wg-routes.sh"

# Settings keys, as used by the api-methods and the web form
FIELDS = (
  "private_key",
  "address",
  "mtu",
  "peer_public_key",
  "peer_preshared_key",
  "peer_endpoint",
  "peer_allowed_ips",
  "peer_persistent_keepalive",
)

INTERFACE_KEYS = {"privatekey": "private_key", "address": "address", "mtu": "mtu"}
PEER_KEYS = {
  "publickey": "peer_public_key",
  "presharedkey": "peer_preshared_key",
  "endpoint": "peer_endpoint",
  "allowedips": "peer_allowed_ips",
  "persistentkeepalive": "peer_persistent_keepalive",
}
# Keys that may appear several times; their values are joined into one list
LIST_FIELDS = ("address", "peer_allowed_ips")

ENDPOINT_RE = re.compile(r"(\[[0-9A-Fa-f:.]+\]|[A-Za-z0-9.-]+):(\d{1,5})")


def empty_settings() -> dict:
  return {field: "" for field in FIELDS}


def parse_config(text: str) -> tuple[dict, list[str]]:
  """Parses a wg-quick config into settings.

  Returns the settings and the lines that were ignored: keys the form does not support
  (DNS, ListenPort, the user's own hooks, ...) and every peer after the first one. The
  routing lines added by build_config() are dropped silently.
  """
  settings = empty_settings()
  ignored: list[str] = []
  section = None
  peers = 0

  for line in text.splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
      continue

    if stripped.startswith("["):
      section = stripped.lower()
      if section == "[peer]":
        peers += 1
      if section not in ("[interface]", "[peer]") or peers > 1:
        ignored.append(stripped)
      continue

    if "=" not in stripped:
      ignored.append(stripped)
      continue

    key, value = (part.strip() for part in stripped.split("=", 1))
    key = key.lower()

    if section == "[interface]":
      if key == "table" and value.lower() == "off":
        continue
      if key in ("postup", "predown") and ROUTING_SCRIPT_MARK in value:
        continue
      field = INTERFACE_KEYS.get(key)
    elif section == "[peer]" and peers == 1:
      field = PEER_KEYS.get(key)
    else:
      field = None

    if not field:
      ignored.append(stripped)
    elif field in LIST_FIELDS and settings[field]:
      settings[field] = f"{settings[field]}, {value}"
    else:
      settings[field] = value

  return settings, ignored


def _is_key(value: str) -> bool:
  try:
    return len(value) == 44 and len(base64.b64decode(value, validate=True)) == 32
  except ValueError:
    return False


def _split(value: str) -> list[str]:
  return [item.strip() for item in value.split(",") if item.strip()]


def _int_in_range(value, low: int, high: int) -> bool:
  try:
    return low <= int(value) <= high
  except (TypeError, ValueError):
    return False


def normalize_settings(settings: dict) -> tuple[dict, str | None]:
  """Validates the settings and brings them to the canonical form.

  Returns (settings, None) or (None, <name of the first invalid field>). Values end up in
  the config file verbatim, so anything not strictly validated here must not be accepted.
  """
  s = {field: str(settings.get(field) or "").strip() for field in FIELDS}

  if not _is_key(s["private_key"]):
    return None, "private_key"

  try:
    addresses = _split(s["address"])
    if not addresses:
      return None, "address"
    s["address"] = ", ".join(str(ipaddress.ip_interface(a)) for a in addresses)
  except ValueError:
    return None, "address"

  if s["mtu"]:
    if not _int_in_range(s["mtu"], 576, 9000):
      return None, "mtu"
    s["mtu"] = str(int(s["mtu"]))

  if not _is_key(s["peer_public_key"]):
    return None, "peer_public_key"

  if s["peer_preshared_key"] and not _is_key(s["peer_preshared_key"]):
    return None, "peer_preshared_key"

  match = ENDPOINT_RE.fullmatch(s["peer_endpoint"])
  if not match or not _int_in_range(match.group(2), 1, 65535):
    return None, "peer_endpoint"

  try:
    networks = _split(s["peer_allowed_ips"])
    if not networks:
      return None, "peer_allowed_ips"
    s["peer_allowed_ips"] = ", ".join(
      str(ipaddress.ip_network(n, strict=False)) for n in networks
    )
  except ValueError:
    return None, "peer_allowed_ips"

  if s["peer_persistent_keepalive"]:
    if not _int_in_range(s["peer_persistent_keepalive"], 0, 65535):
      return None, "peer_persistent_keepalive"
    s["peer_persistent_keepalive"] = str(int(s["peer_persistent_keepalive"]))

  return s, None


def routes_internet(settings: dict) -> bool:
  """Whether the peer's AllowedIPs let plugins reach the internet through the tunnel"""
  return any(n in ("0.0.0.0/0", "::/0") for n in _split(settings.get("peer_allowed_ips") or ""))


def build_config(settings: dict, routes_script: str) -> str:
  """Generates the config file from normalized settings (see normalize_settings)"""
  lines = [
    "# Generated by videoreg (Settings -> WireGuard). Manual edits are lost on the next save.",
    "[Interface]",
    f"PrivateKey = {settings['private_key']}",
    f"Address = {settings['address']}",
  ]
  if settings["mtu"]:
    lines.append(f"MTU = {settings['mtu']}")
  lines += [
    "Table = off",
    f"PostUp = bash {routes_script} up %i",
    f"PreDown = bash {routes_script} down %i",
    "",
    "[Peer]",
    f"PublicKey = {settings['peer_public_key']}",
  ]
  if settings["peer_preshared_key"]:
    lines.append(f"PresharedKey = {settings['peer_preshared_key']}")
  lines += [
    f"Endpoint = {settings['peer_endpoint']}",
    f"AllowedIPs = {settings['peer_allowed_ips']}",
  ]
  if settings["peer_persistent_keepalive"]:
    lines.append(f"PersistentKeepalive = {settings['peer_persistent_keepalive']}")

  return "\n".join(lines) + "\n"
