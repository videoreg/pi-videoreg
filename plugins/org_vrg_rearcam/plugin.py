import asyncio
import time

import plugins.org_vrg_rearcam.const as const
from plugins.org_vrg_rearcam import ble_provisioner
from plugins.org_vrg_rearcam.camera_client import CameraClient
from plugins.org_vrg_rearcam.register_server import RegisterServer
from sdk.service import Plugin


class RearcamPlugin(Plugin):
  """Rear-view WiFi cameras: BLE provisioning, registry, photo/status fetching.

  Cameras are provisioned over BLE (X25519 + AES-256-GCM, see the
  rear-camera-protocol spec), then register themselves at the hub via heartbeat
  POST {hub}/api/register and serve a plain HTTP API on the local network.
  Camera #1 is always the built-in main camera; rear cameras are numbered from 2.
  """

  _register_server: RegisterServer
  _poll_task: asyncio.Task | None = None

  def __init__(self, id, name, runner):
    super().__init__(id, name, runner)
    self._online: dict[str, bool] = {}  # device_id -> online (runtime only)

  async def start(self):
    await super().start()
    self._register_server = RegisterServer(self)
    try:
      await self._register_server.start()
    except Exception as e:
      self.logger.error(f"failed to start register server: {e}", exc_info=True)
    self._poll_task = asyncio.create_task(self._health_poll_loop())

  async def stop(self):
    if self._poll_task:
      self._poll_task.cancel()
      self._poll_task = None
    if self._register_server:
      await self._register_server.stop()
    await super().stop()

  # ---- registry ----

  def _devices(self) -> dict:
    devices = self.state.get(const.STATE_KEY_DEVICES, {})
    return devices if isinstance(devices, dict) else {}

  def _save_devices(self, devices: dict):
    self.state.save({const.STATE_KEY_DEVICES: devices})

  def _find_by_number(self, number: int) -> tuple[str, dict] | tuple[None, None]:
    for device_id, dev in self._devices().items():
      if dev.get("number") == number:
        return device_id, dev
    return None, None

  def list_devices(self) -> list[dict]:
    result = []
    for device_id, dev in sorted(
      self._devices().items(), key=lambda kv: kv[1].get("number", 0)
    ):
      result.append(
        {
          "device_id": device_id,
          "number": dev.get("number"),
          "name": dev.get("name") or "",
          "ble_mac": dev.get("ble_mac") or "",
          "ip": dev.get("ip") or "",
          "firmware": dev.get("firmware") or "",
          "paired_at": dev.get("paired_at"),
          "last_seen": dev.get("last_seen"),
          "online": self._online.get(device_id, False),
        }
      )
    return result

  # ---- heartbeat from cameras ----

  async def on_camera_register(self, device_id: str, ip: str, fw: str):
    devices = self._devices()
    dev = devices.get(device_id)
    if not dev:
      self.logger.warning(f"heartbeat from unknown camera {device_id} ({ip})")
      return
    if ip and dev.get("ip") != ip:
      dev["ip"] = ip
    if fw and dev.get("firmware") != fw:
      dev["firmware"] = fw
    dev["last_seen"] = int(time.time())
    self._save_devices(devices)
    was_online = self._online.get(device_id, False)
    self._online[device_id] = True
    self.logger.info(
      f"camera {device_id} (#{dev.get('number')}) registered: ip={ip} fw={fw}"
      + ("" if was_online else " (online)")
    )

  # ---- provisioning ----

  async def scan_ble(self) -> list[dict]:
    return await ble_provisioner.scan_cameras()

  async def provision(self, mac: str, name: str = "") -> dict:
    """Run the BLE provisioning handshake and register the camera.

    Returns the stored device record. Raises on failure (see methods/provision.py).
    """
    creds_response = await self.api_client.exec("net.wifi_credentials", None, timeout=15)
    if not creds_response.is_ok():
      raise RuntimeError(creds_response.get_error() or "wifi_credentials_failed")
    creds = creds_response.get_data()
    ssid = creds.get("ssid")
    password = creds.get("password") or ""
    hub_ip = creds.get("ip")
    if not ssid or not hub_ip:
      raise RuntimeError("no_wifi_network")
    hub = f"http://{hub_ip}:{const.REGISTER_PORT}"

    result = await ble_provisioner.provision(mac, ssid, password, hub, logger=self.logger)
    ip = result.get("ip", "")

    # The BLE result carries only the IP; fetch the identity over HTTP.
    device_id = ""
    firmware = ""
    if ip:
      device_id, firmware = await self._await_camera_identity(ip)

    devices = self._devices()

    # Re-provisioning an already paired camera keeps its number.
    existing_id = None
    for did, dev in devices.items():
      if dev.get("ble_mac") == mac.upper() or (device_id and did == device_id):
        existing_id = did
        break

    if existing_id:
      device_id = device_id or existing_id
      dev = devices.pop(existing_id)
      number = dev.get("number")
    else:
      number = max(
        [d.get("number", const.FIRST_CAMERA_NUMBER - 1) for d in devices.values()]
        + [const.FIRST_CAMERA_NUMBER - 1]
      ) + 1

    if not device_id:
      device_id = f"pending-{mac.replace(':', '').lower()}"

    devices[device_id] = {
      "number": number,
      "name": name or f"Camera {number}",
      "ble_mac": mac.upper(),
      "ip": ip,
      "firmware": firmware,
      "paired_at": int(time.time()),
      "last_seen": int(time.time()),
    }
    self._save_devices(devices)
    self._online[device_id] = bool(ip)
    self.logger.info(f"camera provisioned: {device_id} as #{number} ip={ip}")
    return {"device_id": device_id, **devices[device_id], "online": self._online[device_id]}

  async def _await_camera_identity(self, ip: str) -> tuple[str, str]:
    """Poll /health until the camera's HTTP API is up; return (device_id, fw)."""
    client = CameraClient(ip, timeout=5)
    for _ in range(10):
      try:
        health = await client.get_health()
        return health.get("device_id", ""), health.get("fw", "")
      except Exception:
        await asyncio.sleep(2)
    self.logger.warning(f"camera at {ip} did not answer /health after provisioning")
    return "", ""

  def forget(self, number: int) -> bool:
    device_id, dev = self._find_by_number(number)
    if not device_id:
      return False
    devices = self._devices()
    del devices[device_id]
    self._save_devices(devices)
    self._online.pop(device_id, None)
    self.logger.info(f"camera {device_id} (#{number}) forgotten")
    return True

  # ---- photo / status ----

  async def take_photo(self, number: int) -> str:
    """Fetch a JPEG from camera #N and save it to the plugin data dir."""
    device_id, dev = self._find_by_number(number)
    if not dev or not dev.get("ip"):
      raise RuntimeError("camera_not_found")
    jpeg = await CameraClient(dev["ip"]).get_photo()
    path = self.runner.videoreg.plugin_private_path(
      self.id, f"rear_photo_{number}_{int(time.time())}.jpg"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(jpeg)
    return str(path)

  async def get_camera_status(self, number: int) -> dict:
    device_id, dev = self._find_by_number(number)
    if not dev or not dev.get("ip"):
      raise RuntimeError("camera_not_found")
    client = CameraClient(dev["ip"])
    health, status = await asyncio.gather(client.get_health(), client.get_status())
    return {**health, **status, "number": number, "device_id": device_id}

  # ---- health polling ----

  async def _health_poll_loop(self):
    try:
      while self.runner.is_running():
        await asyncio.sleep(const.HEALTH_POLL_SECONDS)
        for device_id, dev in self._devices().items():
          ip = dev.get("ip")
          if not ip:
            self._online[device_id] = False
            continue
          try:
            health = await CameraClient(ip, timeout=5).get_health()
            self._online[device_id] = True
            fw = health.get("fw", "")
            if fw and fw != dev.get("firmware"):
              devices = self._devices()
              if device_id in devices:
                devices[device_id]["firmware"] = fw
                self._save_devices(devices)
          except Exception:
            if self._online.get(device_id):
              self.logger.info(f"camera {device_id} (#{dev.get('number')}) went offline")
            self._online[device_id] = False
    except asyncio.CancelledError:
      pass
