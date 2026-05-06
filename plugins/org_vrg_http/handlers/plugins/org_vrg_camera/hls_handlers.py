"""HLS file handler — serves live stream segments from the camera plugin's private dir"""

import os

from aiohttp import web


async def handle_get_hls(request: web.Request):
  filename = request.match_info["filename"]
  if "/" in filename or ".." in filename:
    raise web.HTTPForbidden()

  if filename.endswith(".m3u8"):
    content_type = "application/vnd.apple.mpegurl"
  elif filename.endswith(".ts"):
    content_type = "video/mp2t"
  else:
    raise web.HTTPForbidden()

  hls_dir = request.app["videoreg"].plugin_private_path("org_vrg_camera", "hls")
  path = os.path.join(str(hls_dir), filename)
  if not os.path.isfile(path):
    raise web.HTTPNotFound()

  return web.FileResponse(
    path,
    headers={
      "Cache-Control": "no-store",
      "Content-Type": content_type,
    },
  )
