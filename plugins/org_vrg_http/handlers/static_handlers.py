"""Static file handlers"""

import json
import os
import re

import aiofiles
from aiohttp import web

from plugins.org_vrg_http.bundle import build_bundle
from plugins.org_vrg_http.manifest_reader import collect_dashboard_blocks, enabled_plugin_ids


def _build_bootstrap_script(http_manifests: list) -> str:
  """Build the inline bootstrap `<script>` injected into index.html.

  Emits `window.__vrgMenu` (menu data), `window.__vrgDashboard` (ordered
  dashboard block structure) and `window.__vrgComponents` — a string→object
  bridge written with literal Vue component identifiers, resolved lexically
  from bundle.js.
  """
  menu: list = []
  menu_settings: list = []
  component_names: list[str] = []

  def _collect(items, dst):
    for item in items or []:
      dst.append(item)
      name = item.get("component")
      if name and name not in component_names:
        component_names.append(name)

  for config in http_manifests or []:
    http = config["http"]
    _collect(http.get("menu"), menu)
    _collect(http.get("menu_settings"), menu_settings)
    # Dashboard blocks are not menu items, but their components must still be
    # resolvable through the string→object bridge (block.component arrives as a
    # name string). Runtime-inserted tiles pass the component object directly and
    # so are not declared in the manifest / bridged here.
    for entry in http.get("dashboard") or []:
      name = entry.get("component")
      if name and name not in component_names:
        component_names.append(name)

  # Structure of the initial dashboard blocks (component + order), sent to the
  # frontend so it can render tiles (with loading shimmers) before their data
  # arrives from /api/dashboard/status. Runtime-only blocks are excluded.
  dashboard = [
    {"key": b["key"], "component": b["component"], "order": b["order"]}
    for b in collect_dashboard_blocks(http_manifests)
  ]

  menu_json = json.dumps({"menu": menu, "menu_settings": menu_settings}, ensure_ascii=False)
  dashboard_json = json.dumps(dashboard, ensure_ascii=False)

  # Bridge string component name → object using the identifiers defined in
  # bundle.js (or still-present static scripts). Each assignment is guarded so a
  # not-yet-loaded component cannot break the rest of the bootstrap.
  bridge_lines = ["  window.__vrgComponents = {};"]
  for name in component_names:
    bridge_lines.append(
      f"  try {{ window.__vrgComponents.{name} = {name}; }} catch (e) {{}}"
    )
  bridge = "\n".join(bridge_lines)

  return (
    "<script>\n"
    f"  window.__vrgMenu = {menu_json};\n"
    f"  window.__vrgDashboard = {dashboard_json};\n"
    f"{bridge}\n"
    "</script>"
  )


async def handle_index(request: web.Request):
  """Main page"""
  static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
  index_path = os.path.join(static_dir, "index.html")

  if not os.path.isfile(index_path):
    raise web.HTTPNotFound(text="Index page not found")

  async with aiofiles.open(index_path, encoding="utf-8") as f:
    content = await f.read()

  version = request.app["static_version"]
  content = re.sub(r'(/static/[^"]+)"', rf'\1?v={version}"', content)

  # Inject the manifest-driven bootstrap (menu + component bridge)
  bootstrap = _build_bootstrap_script(request.app.get("http_manifests"))
  content = content.replace("<!-- VRG_BOOTSTRAP -->", bootstrap)

  return web.Response(text=content, content_type="text/html", charset="utf-8")


async def handle_static(request: web.Request):
  """Static file handler"""
  filename = request.match_info["filename"]

  # Path traversal protection
  if ".." in filename or filename.startswith("/"):
    raise web.HTTPForbidden()

  static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
  file_path = os.path.join(static_dir, filename)

  # Ensure the file is inside the static directory
  if not os.path.abspath(file_path).startswith(os.path.abspath(static_dir)):
    raise web.HTTPForbidden()

  # bundle.js is generated on demand (cold start) from enabled plugin components
  if filename == "js/bundle.js" and not os.path.isfile(file_path):
    videoreg = request.app["videoreg"]
    plugins_dir = videoreg.app_path("plugins")
    enabled_ids = enabled_plugin_ids(videoreg.manifest)
    build_bundle(plugins_dir, videoreg.app_path(
      "plugins/org_vrg_http/static/js/bundle.js"
    ), enabled_ids)

  if not os.path.isfile(file_path):
    raise web.HTTPNotFound(text="File not found")

  # Determine content type by extension
  content_type = "application/octet-stream"
  if filename.endswith(".css"):
    content_type = "text/css"
  elif filename.endswith(".js"):
    content_type = "application/javascript"
  elif filename.endswith(".html"):
    content_type = "text/html"
  elif filename.endswith(".png"):
    content_type = "image/png"
  elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
    content_type = "image/jpeg"
  elif filename.endswith(".svg"):
    content_type = "image/svg+xml"
  elif filename.endswith(".ico"):
    content_type = "image/x-icon"

  cache_headers = {"Cache-Control": "public, max-age=31536000, immutable"}

  # Read and serve the file
  if content_type.startswith("text/") or content_type == "application/javascript":
    async with aiofiles.open(file_path, encoding="utf-8") as f:
      content = await f.read()
    response = web.Response(
      text=content, content_type=content_type, charset="utf-8", headers=cache_headers
    )
  else:
    async with aiofiles.open(file_path, "rb") as f:
      content = await f.read()
    response = web.Response(
      body=content, content_type=content_type, headers=cache_headers
    )

  # The largest assets (~220 KB bundle.js, ~hundreds-of-KB vue.global.js) are
  # highly compressible text; compress them on the fly (rarely requested thanks
  # to immutable caching).
  if filename in ("js/bundle.js", "vue.global.js"):
    response.enable_compression()

  return response
