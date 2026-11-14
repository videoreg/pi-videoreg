"""BLE provisioning client for rear cameras.

Implements the hub side of the rear-camera-protocol provisioning handshake:
  1. read the camera's ephemeral X25519 public key (pubkey characteristic),
  2. write our own ephemeral X25519 public key,
  3. session key = raw 32-byte ECDH shared secret (AES-256-GCM),
  4. write the encrypted credentials frame in MTU-sized chunks,
  5. wait for the encrypted result notification ("connected" / "error").

Wire framing in both directions: uint16_le total_len || nonce(12) || ct || tag(16),
where total_len covers the whole frame including the length field itself.
"""

import asyncio
import json
import os
import struct

import plugins.org_vrg_rearcam.const as const

try:
  from bleak import BleakClient, BleakScanner
  from cryptography.hazmat.primitives import serialization
  from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
  from cryptography.hazmat.primitives.ciphers.aead import AESGCM

  PROV_AVAILABLE = True
except Exception:  # bleak/cryptography may be absent on a dev host
  BleakClient = None
  PROV_AVAILABLE = False


class ProvisionError(Exception):
  """Provisioning failed; str(self) is a machine-readable reason."""


def is_supported() -> bool:
  return PROV_AVAILABLE


async def scan_cameras(duration: float = const.BLE_SCAN_SECONDS) -> list[dict]:
  """Return advertising rear cameras as [{mac, name, rssi}], strongest first."""
  if not PROV_AVAILABLE:
    raise ProvisionError("bleak_not_available")

  found: dict[str, dict] = {}

  def cb(device, adv):
    name = getattr(adv, "local_name", None) or getattr(device, "name", None)
    has_service = const.BLE_SERVICE_UUID in (getattr(adv, "service_uuids", None) or [])
    if not ((name and name.startswith(const.BLE_NAME_PREFIX)) or has_service):
      return
    mac = (getattr(device, "address", "") or "").upper()
    if not mac:
      return
    found[mac] = {
      "mac": mac,
      "name": name,
      "rssi": getattr(adv, "rssi", None),
    }

  scanner = BleakScanner(detection_callback=cb)
  await scanner.start()
  try:
    await asyncio.sleep(duration)
  finally:
    await scanner.stop()

  devices = list(found.values())
  devices.sort(key=lambda d: (d.get("rssi") is None, -(d.get("rssi") or 0)))
  return devices


async def provision(mac: str, ssid: str, password: str, hub: str, token: str, logger=None) -> dict:
  """Provision the camera at `mac` with WiFi credentials, the hub URL and token.

  `token` is the per-camera access token the camera will present on all HTTP
  requests (see the protocol spec); the hub generates it per provisioning, so
  re-provisioning rotates the token.

  Returns {"status": "connected", "ip": ...} on success; raises ProvisionError
  with the device-reported reason ("bad_password" / "ssid_not_found" / "timeout")
  or a local error code otherwise.
  """
  if not PROV_AVAILABLE:
    raise ProvisionError("bleak_not_available")

  rx_buf = bytearray()
  rx_expected = 0
  result_event = asyncio.Event()
  result_frame: dict[str, bytes] = {}

  def on_notify(_, data: bytes):
    nonlocal rx_expected
    rx_buf.extend(data)
    if rx_expected == 0 and len(rx_buf) >= 2:
      rx_expected = rx_buf[0] | (rx_buf[1] << 8)
    if rx_expected and len(rx_buf) >= rx_expected:
      result_frame["data"] = bytes(rx_buf[:rx_expected])
      result_event.set()

  try:
    async with BleakClient(mac, timeout=20.0) as client:
      await client.start_notify(const.BLE_CHR_RESULT_UUID, on_notify)

      # bleak 3.x does not learn the negotiated MTU by itself (mtu_size
      # defaults to 23); acquiring it once also triggers the MTU exchange.
      try:
        await client._acquire_mtu()
      except Exception:
        pass
      if logger:
        logger.info(f"provisioning {mac}: connected, mtu={client.mtu_size}")

      device_pub = bytes(await client.read_gatt_char(const.BLE_CHR_PUBKEY_UUID))
      if len(device_pub) != 32:
        raise ProvisionError("bad_pubkey")

      priv = X25519PrivateKey.generate()
      my_pub = priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
      )
      await client.write_gatt_char(const.BLE_CHR_PUBKEY_UUID, my_pub, response=True)

      shared = priv.exchange(X25519PublicKey.from_public_bytes(device_pub))
      aes = AESGCM(shared)

      creds = json.dumps({"ssid": ssid, "password": password, "hub": hub, "token": token}).encode()
      nonce = os.urandom(12)
      blob = struct.pack("<H", 2 + 12 + len(creds) + 16) + nonce + aes.encrypt(nonce, creds, None)

      chunk = client.mtu_size - 3
      for off in range(0, len(blob), chunk):
        await client.write_gatt_char(const.BLE_CHR_CREDS_UUID, blob[off : off + chunk], response=True)

      try:
        await asyncio.wait_for(result_event.wait(), timeout=const.BLE_PROVISION_TIMEOUT)
      except TimeoutError:
        raise ProvisionError("timeout") from None

      data = result_frame["data"]
      payload = data[2:]
      try:
        plain = aes.decrypt(payload[:12], payload[12:], None)
        result = json.loads(plain.decode())
      except Exception:
        raise ProvisionError("bad_result") from None

      if result.get("status") == "connected":
        return result
      raise ProvisionError(result.get("reason") or "unknown")
  except ProvisionError:
    raise
  except Exception as e:
    raise ProvisionError(f"ble_error: {e}") from e
