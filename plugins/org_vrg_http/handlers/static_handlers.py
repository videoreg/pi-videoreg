"""Static file handlers"""

import os
import re

import aiofiles
from aiohttp import web


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
    return web.Response(
      text=content, content_type=content_type, charset="utf-8", headers=cache_headers
    )
  else:
    async with aiofiles.open(file_path, "rb") as f:
      content = await f.read()
    return web.Response(body=content, content_type=content_type, headers=cache_headers)
