"""User management handlers"""

import json
import re

from aiohttp import web


async def handle_get_users(request: web.Request):
  """GET /api/users — list users with plugin_fields"""
  user_manager = request.app["user_manager"]
  users = user_manager.get_all_users()
  return web.json_response({"users": users})


async def handle_patch_user_plugin_fields(request: web.Request):
  """PATCH /api/users/{username}/plugin-fields/{plugin} — update plugin fields for a user"""
  user_manager = request.app["user_manager"]
  username = request.match_info["username"]
  plugin = request.match_info["plugin"]

  if not user_manager.user_exists(username):
    return web.Response(
      status=404, text=json.dumps({"error": "User not found"}), content_type="application/json"
    )

  try:
    fields = await request.json()
  except json.JSONDecodeError:
    return web.Response(
      status=400, text=json.dumps({"error": "Invalid JSON"}), content_type="application/json"
    )

  user_manager.set_plugin_fields(username, plugin, fields)
  return web.json_response({"status": "ok"})


async def handle_post_user(request: web.Request):
  """POST /api/users — add a user"""
  user_manager = request.app["user_manager"]

  try:
    body = await request.json()
  except json.JSONDecodeError:
    return web.Response(
      status=400, text=json.dumps({"error": "Invalid JSON"}), content_type="application/json"
    )

  username = (body.get("username") or "").strip()
  password = (body.get("password") or "").strip()

  if not username or not password:
    return web.Response(
      status=400,
      text=json.dumps({"error": "Username and password are required"}),
      content_type="application/json",
    )

  if not re.fullmatch(r"[a-zA-Z0-9_-]+", username):
    return web.Response(
      status=400,
      text=json.dumps({"error": "Username can only contain latin letters, digits, - and _"}),
      content_type="application/json",
    )

  added = user_manager.add_user(username, password)
  if not added:
    return web.Response(
      status=409, text=json.dumps({"error": "User already exists"}), content_type="application/json"
    )

  return web.json_response({"status": "ok"})


async def handle_delete_user(request: web.Request):
  """DELETE /api/users/{username} — delete a user"""
  user_manager = request.app["user_manager"]
  username = request.match_info["username"]

  try:
    deleted = user_manager.delete_user(username)
  except ValueError as e:
    return web.Response(
      status=400, text=json.dumps({"error": str(e)}), content_type="application/json"
    )

  if not deleted:
    return web.Response(
      status=404, text=json.dumps({"error": "User not found"}), content_type="application/json"
    )

  return web.json_response({"status": "ok"})
