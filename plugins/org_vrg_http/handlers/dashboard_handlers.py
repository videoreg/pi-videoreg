"""Dashboard status handler.

The dashboard is assembled from blocks declared decoratively in each plugin's
`manifest.yaml` under `http.dashboard` (see `manifest_reader.collect_dashboard_blocks`).
The static block *structure* (component + order) is injected into the page as
`window.__vrgDashboard` by `static_handlers`, so the frontend can render the
tiles (with loading shimmers) immediately. This handler resolves only the block
*data* — one videoreg-api call per block that declares a `method` — and returns
a `{ "<block key>": <data> }` map. The http plugin stays agnostic about which
plugins exist. Blocks added imperatively at runtime (e.g. captured media) are
not manifest-declared and never reach this handler.
"""

import asyncio

from aiohttp import web

from plugins.org_vrg_http.manifest_reader import collect_dashboard_blocks

# Default per-block data-resolution timeout, seconds. At cold first load most
# block methods spawn a subprocess (rpicam-hello, nmcli, wg/ip) or read hardware
# (I2C), which legitimately takes a few seconds — camera.get_info alone caps its
# own rpicam probe at 3s. A tighter budget dropped such merely-slow-but-successful
# calls, so the tile falsely rendered as off ("disabled"/"no data"). This gates
# how long the (gathered) endpoint waits on its slowest block, so it stays bounded
# rather than short. Blocks that can be slower still (the modem reading info over
# AT under weak signal) declare a larger `timeout` in their manifest.
DEFAULT_BLOCK_TIMEOUT = 5.0


async def handle_get_dashboard_status(request: web.Request):
  """Data for every manifest-declared dashboard block, keyed by block key."""
  logger = request.app["logger"]
  api_client = request.app["api_client"]
  http_manifests = request.app.get("http_manifests")

  # Only blocks that declare a data method are resolved here.
  data_blocks = [b for b in collect_dashboard_blocks(http_manifests) if b["method"]]

  responses = await asyncio.gather(
    *(
      api_client.exec(b["method"], {}, timeout=b.get("timeout") or DEFAULT_BLOCK_TIMEOUT)
      for b in data_blocks
    ),
    return_exceptions=True,
  )

  data_by_key: dict = {}
  for block, response in zip(data_blocks, responses):
    if isinstance(response, Exception):
      logger.warning(f"Dashboard: {block['method']} error: {response}")
    elif response.is_ok():
      data_by_key[block["key"]] = response.get_data()

  return web.json_response(data_by_key)


async def handle_get_statusbar_status(request: web.Request):
  """Minimal status for the global status bar (camera + power only)"""
  logger = request.app["logger"]
  api_client = request.app["api_client"]

  (
    camera_response,
    power_response,
    last_media_response,
  ) = await asyncio.gather(
    api_client.exec("camera.get_info", {}),
    api_client.exec("power.get_status", {}),
    api_client.exec("camera.get_last_media", {}),
    return_exceptions=True,
  )

  result = {
    "camera": None,
    "power": None,
    "last_media": None,
  }

  if isinstance(camera_response, Exception):
    logger.warning(f"Statusbar: camera info error: {camera_response}")
  elif camera_response.is_ok():
    result["camera"] = camera_response.get_data()

  if isinstance(power_response, Exception):
    logger.warning(f"Statusbar: power status error: {power_response}")
  elif power_response.is_ok():
    result["power"] = power_response.get_data()

  if isinstance(last_media_response, Exception):
    logger.warning(f"Statusbar: last media error: {last_media_response}")
  elif last_media_response.is_ok():
    result["last_media"] = last_media_response.get_data()

  return web.json_response(result)
