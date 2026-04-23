"""Authorization handlers"""

import json

from aiohttp import web


async def handle_login(request: web.Request):
  """Login"""
  jwt_handler = request.app["jwt_handler"]
  user_manager = request.app["user_manager"]
  logger = request.app["logger"]

  try:
    data = await request.json()
  except json.JSONDecodeError:
    return web.Response(
      status=400, text='{"error": "Invalid JSON"}', content_type="application/json"
    )

  username = data.get("username")
  password = data.get("password")

  if not username or not password:
    return web.Response(
      status=400,
      text='{"error": "Username and password are required"}',
      content_type="application/json",
    )

  # Authenticate
  if not user_manager.authenticate(username, password):
    return web.Response(
      status=401, text='{"error": "Invalid credentials"}', content_type="application/json"
    )

  # Generate tokens
  access_token = jwt_handler.create_access_token(username)
  refresh_token = jwt_handler.create_refresh_token(username)

  response_data = {
    "access_token": access_token,
    "refresh_token": refresh_token,
    "token_type": "Bearer",
  }

  logger.info(f"User '{username}' logged in")

  # Set HTTP-only cookies for automatic authorization
  response = web.Response(text=json.dumps(response_data), content_type="application/json")

  # Access token in HTTP-only cookie (7 days)
  response.set_cookie(
    "access_token",
    access_token,
    max_age=7 * 24 * 60 * 60,
    httponly=True,
    secure=True,
    samesite="Strict",
  )

  # Refresh token in HTTP-only cookie (30 days)
  response.set_cookie(
    "refresh_token",
    refresh_token,
    max_age=30 * 24 * 60 * 60,
    httponly=True,
    secure=True,
    samesite="Strict",
  )

  return response


async def handle_logout(request: web.Request):
  """Logout"""
  response = web.Response(
    text='{"message": "Logged out successfully"}', content_type="application/json"
  )

  # Delete cookies
  response.del_cookie("access_token")
  response.del_cookie("refresh_token")

  return response


async def handle_refresh(request: web.Request):
  """Refresh access token"""
  jwt_handler = request.app["jwt_handler"]
  user_manager = request.app["user_manager"]

  # Get refresh token from HTTP-only cookie
  refresh_token = request.cookies.get("refresh_token")

  if not refresh_token:
    return web.Response(
      status=401, text='{"error": "Refresh token not found"}', content_type="application/json"
    )

  # Verify refresh token
  username = jwt_handler.verify_token(refresh_token, token_type="refresh")

  if username is None:
    return web.Response(
      status=401,
      text='{"error": "Invalid or expired refresh token"}',
      content_type="application/json",
    )

  # Check that the user exists
  if not user_manager.user_exists(username):
    return web.Response(
      status=401, text='{"error": "User not found"}', content_type="application/json"
    )

  # Generate new access token
  access_token = jwt_handler.create_access_token(username)

  response_data = {"access_token": access_token, "token_type": "Bearer"}

  # Update HTTP-only cookie
  response = web.Response(text=json.dumps(response_data), content_type="application/json")

  # Access token in HTTP-only cookie (7 days)
  response.set_cookie(
    "access_token",
    access_token,
    max_age=7 * 24 * 60 * 60,
    httponly=True,
    secure=True,
    samesite="Strict",
  )

  return response


async def handle_change_password(request: web.Request):
  """Change password (requires authorization)"""
  user_manager = request.app["user_manager"]
  logger = request.app["logger"]
  username = request.get("user")  # Set by middleware

  try:
    data = await request.json()
  except json.JSONDecodeError:
    return web.Response(
      status=400, text='{"error": "Invalid JSON"}', content_type="application/json"
    )

  old_password = data.get("old_password")
  new_password = data.get("new_password")

  if not old_password or not new_password:
    return web.Response(
      status=400,
      text='{"error": "Old password and new password are required"}',
      content_type="application/json",
    )

  # Validate minimum new password length
  if len(new_password) < 6:
    return web.Response(
      status=400,
      text='{"error": "New password must be at least 6 characters long"}',
      content_type="application/json",
    )

  # Change password
  success = user_manager.change_password(username, old_password, new_password)

  if not success:
    return web.Response(
      status=401, text='{"error": "Invalid old password"}', content_type="application/json"
    )

  logger.info(f"User '{username}' changed password")

  return web.Response(
    text='{"message": "Password changed successfully"}', content_type="application/json"
  )


async def handle_me(request: web.Request):
  """Current user info (requires authorization)"""
  user_manager = request.app["user_manager"]
  username = request.get("user")  # Set by middleware

  user_info = user_manager.get_user_info(username)

  if user_info is None:
    return web.Response(
      status=404, text='{"error": "User not found"}', content_type="application/json"
    )

  return web.Response(text=json.dumps(user_info), content_type="application/json")
