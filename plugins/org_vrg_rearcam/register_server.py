"""Hub-side registration server.

Rear cameras POST {"device_id", "ip", "fw"} to {hub}/api/register right after
they (re)connect to WiFi (heartbeat, see the rear-camera-protocol spec).
This server listens on REGISTER_PORT and forwards registrations to the plugin.
"""

import time
from datetime import datetime

from aiohttp import web

import plugins.org_vrg_rearcam.const as const


class RegisterServer:
  def __init__(self, plugin):
    self._plugin = plugin
    self._runner = None

  async def start(self):
    app = web.Application()
    app.router.add_post(const.REGISTER_PATH, self._handle_register)
    app.router.add_get("/api/health", self._handle_health)
    app.router.add_get("/api/time", self._handle_time)
    self._runner = web.AppRunner(app)
    await self._runner.setup()
    site = web.TCPSite(self._runner, host="0.0.0.0", port=const.REGISTER_PORT)
    await site.start()
    self._plugin.logger.info(f"register server listening on :{const.REGISTER_PORT}")

  async def stop(self):
    if self._runner:
      await self._runner.cleanup()
      self._runner = None

  async def _handle_health(self, request: web.Request):
    return web.json_response({"status": "ok"})

  @staticmethod
  def _bearer_token(request: web.Request) -> str:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
      return header[len("Bearer "):].strip()
    return ""

  async def _handle_time(self, request: web.Request):
    """Current time for cameras without NTP (see the protocol spec).

    Requires the same bearer token as /api/register. `epoch` is UTC;
    `utc_offset_s` is the hub's current local offset including DST, so the
    camera can show local time without a timezone database.
    """
    if not self._plugin.token_known(self._bearer_token(request)):
      return web.json_response({"error": "unauthorized"}, status=401)
    now = time.time()
    offset = datetime.now().astimezone().utcoffset()
    return web.json_response(
        {
            "epoch": int(now),
            "utc_offset_s": int(offset.total_seconds()) if offset else 0,
        }
    )

  async def _handle_register(self, request: web.Request):
    try:
      data = await request.json()
    except Exception:
      return web.json_response({"error": "invalid_json"}, status=400)

    device_id = data.get("device_id")
    ip = data.get("ip")
    fw = data.get("fw")
    if not isinstance(device_id, str) or not device_id:
      return web.json_response({"error": "device_id_required"}, status=400)

    accepted = await self._plugin.on_camera_register(
      device_id=device_id,
      ip=ip if isinstance(ip, str) else "",
      fw=fw if isinstance(fw, str) else "",
      token=self._bearer_token(request),
    )
    if not accepted:
      return web.json_response({"error": "unauthorized"}, status=401)
    return web.json_response({"status": "ok"})
