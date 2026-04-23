"""Handlers for media files (video, photos, and GPS tracks)"""

import os
from pathlib import Path

import aiofiles
from aiohttp import web

CHUNK_SIZE = 64 * 1024  # 64 KB


async def handle_video(request: web.Request):
  """Video handler with Range request support"""
  videoreg = request.app["videoreg"]
  video_name = request.match_info["name"]

  # Path traversal protection
  if ".." in video_name or "/" in video_name:
    raise web.HTTPForbidden()

  video_path = videoreg.mp4_path(f"{video_name}.mp4")

  if not video_path.is_file():
    raise web.HTTPNotFound(text="Video not found")

  file_size = os.path.getsize(str(video_path))

  # Handle Range requests
  range_header = request.headers.get("Range")

  if range_header:
    try:
      range_spec = range_header.replace("bytes=", "")
      start_str, end_str = range_spec.split("-")
      start = int(start_str) if start_str else 0
      end = int(end_str) if end_str else file_size - 1
    except ValueError:
      raise web.HTTPBadRequest()

    if start >= file_size:
      raise web.HTTPRequestRangeNotSatisfiable()

    end = min(end, file_size - 1)
    content_length = end - start + 1

    response = web.StreamResponse(
      status=206,
      headers={
        "Content-Type": "video/mp4",
        "Content-Length": str(content_length),
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=31536000, immutable",
      },
    )
    await response.prepare(request)

    try:
      async with aiofiles.open(video_path, "rb") as f:
        await f.seek(start)
        remaining = content_length
        while remaining > 0:
          chunk = await f.read(min(CHUNK_SIZE, remaining))
          if not chunk:
            break
          await response.write(chunk)
          remaining -= len(chunk)
    except (ConnectionResetError, BrokenPipeError, ConnectionError):
      # Client disconnected — normal for video streaming
      pass

    return response

  # Full response
  response = web.StreamResponse(
    headers={
      "Content-Type": "video/mp4",
      "Content-Length": str(file_size),
      "Accept-Ranges": "bytes",
      "Cache-Control": "public, max-age=31536000, immutable",
    }
  )
  await response.prepare(request)

  try:
    async with aiofiles.open(video_path, "rb") as f:
      while chunk := await f.read(CHUNK_SIZE):
        await response.write(chunk)
  except (ConnectionResetError, BrokenPipeError, ConnectionError):
    # Client disconnected — normal for video streaming
    pass

  return response


async def handle_photo(request: web.Request):
  """Photo handler"""
  videoreg = request.app["videoreg"]
  photo_name = request.match_info["name"]

  # Path traversal protection
  if ".." in photo_name or "/" in photo_name:
    raise web.HTTPForbidden()

  photo_path = videoreg.jpeg_path(f"{photo_name}.jpg")

  if not photo_path.is_file():
    raise web.HTTPNotFound(text="Photo not found")

  stat = os.stat(str(photo_path))
  file_size = stat.st_size
  etag = f'"{int(stat.st_mtime)}-{file_size}"'

  if request.headers.get("If-None-Match") == etag:
    return web.Response(status=304)

  # Serve photo in full
  async with aiofiles.open(photo_path, "rb") as f:
    content = await f.read()

  return web.Response(
    body=content,
    headers={
      "Content-Type": "image/jpeg",
      "Content-Length": str(file_size),
      "Cache-Control": "public, max-age=31536000, immutable",
      "ETag": etag,
    },
  )


async def handle_fave_photo(request: web.Request):
  """Favorites photo handler"""
  videoreg = request.app["videoreg"]
  photo_name = request.match_info["name"]

  # Path traversal protection
  if ".." in photo_name or "/" in photo_name:
    raise web.HTTPForbidden()

  photo_path = videoreg.jpeg_fave_path(f"{photo_name}.jpg")

  if not photo_path.is_file():
    raise web.HTTPNotFound(text="Photo not found")

  stat = os.stat(str(photo_path))
  file_size = stat.st_size
  etag = f'"{int(stat.st_mtime)}-{file_size}"'

  if request.headers.get("If-None-Match") == etag:
    return web.Response(status=304)

  # Serve photo in full
  async with aiofiles.open(photo_path, "rb") as f:
    content = await f.read()

  return web.Response(
    body=content,
    headers={
      "Content-Type": "image/jpeg",
      "Content-Length": str(file_size),
      "Cache-Control": "public, max-age=31536000, immutable",
      "ETag": etag,
    },
  )


async def handle_gps_track(request: web.Request):
  """Download a GPX track file"""
  videoreg = request.app["videoreg"]

  name = request.match_info["name"]

  if ".." in name or "/" in name or "\\" in name:
    raise web.HTTPForbidden()

  file_path = Path(videoreg.gps_path()) / f"{name}.gpx"

  if not file_path.is_file():
    raise web.HTTPNotFound(text="GPS track not found")

  return web.FileResponse(
    path=file_path, headers={"Content-Disposition": f'attachment; filename="{name}.gpx"'}
  )
